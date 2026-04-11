"""Wake word detection (Step 10).

Goal:
- Lightweight wake word trigger for tray/background usage
- No heavy ML wake word models
- No paid SDKs

Design:
- Uses Vosk with a small phrase grammar to detect wake phrases from short, continuous audio chunks.
- On detection, it calls a callback (which should trigger the existing one-shot voice pipeline).

Important:
- This is *not* continuous command listening. It only listens for wake phrases.
- It should not run in CLI mode by default.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional


@dataclass(frozen=True)
class WakewordMatch:
    matched: bool
    keyword: str = ""


class WakewordDetector:
    """Detect a wakeword in already-transcribed text."""

    def __init__(self, phrases: Iterable[str]) -> None:
        self._phrases = [p.strip().lower() for p in phrases if isinstance(p, str) and p.strip()]

    def detect(self, text: str) -> WakewordMatch:
        t = (text or "").strip().lower()
        if not t:
            return WakewordMatch(matched=False)

        for p in self._phrases:
            if p and p in t:
                return WakewordMatch(matched=True, keyword=p)

        return WakewordMatch(matched=False)


@dataclass(frozen=True)
class WakeWordStatus:
    ok: bool
    error: Optional[str] = None


class WakeWordListener:
    """Background wake word listener using `sounddevice` + Vosk.

    Uses a phrase-limited grammar to keep CPU usage low.
    """

    def __init__(
        self,
        *,
        phrases: Iterable[str],
        on_wake: Callable[[str], None],
        sample_rate_hz: int = 16000,
        device_index: Optional[int] = None,
        channels: int = 1,
        cooldown_seconds: float = 2.0,
    ) -> None:
        self._phrases = [p.strip().lower() for p in phrases if isinstance(p, str) and p.strip()]
        self._on_wake = on_wake
        self._sample_rate_hz = int(sample_rate_hz)
        self._device_index = device_index
        self._channels = int(channels)
        self._cooldown_seconds = float(cooldown_seconds)

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._sd = None
        self._rec = None
        self._model = None

    def is_running(self) -> bool:
        t = self._thread
        return t is not None and t.is_alive() and not self._stop.is_set()

    def start(self) -> WakeWordStatus:
        """Start wake listening in a background thread."""

        with self._lock:
            if self.is_running():
                return WakeWordStatus(ok=True)

            if not self._phrases:
                return WakeWordStatus(ok=False, error="No wake word phrases configured.")

            if self._sample_rate_hz <= 0:
                return WakeWordStatus(ok=False, error="Invalid sample rate.")

            print(f"WakeWordListener.start: sample_rate_hz={self._sample_rate_hz} channels={self._channels} device_index={self._device_index}")
            print(f"WakeWordListener.start: phrases={self._phrases}")

            try:
                import sounddevice as sd  # type: ignore

                self._sd = sd
            except Exception as exc:
                return WakeWordStatus(ok=False, error=f"sounddevice import failed: {exc}")

            # Resolve model using the same logic as the main Vosk STT path.
            try:
                from app.input.voice.speech_to_text import VoskSpeechToText

                stt = VoskSpeechToText()
                self._model = stt._get_model()  # type: ignore[attr-defined]
            except Exception as exc:
                return WakeWordStatus(ok=False, error=str(exc))

            try:
                from vosk import KaldiRecognizer  # type: ignore

                # Phrase grammar (required): only these wake phrases.
                grammar = json.dumps(self._phrases)
                print(f"Wake recognizer grammar: {grammar}")

                self._rec = KaldiRecognizer(self._model, float(self._sample_rate_hz), grammar)
            except Exception as exc:
                return WakeWordStatus(ok=False, error=f"vosk init failed: {exc}")

            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="wakeword", daemon=True)
            self._thread.start()
            return WakeWordStatus(ok=True)

    def stop(self) -> None:
        """Stop wake listening."""

        with self._lock:
            self._stop.set()
            t = self._thread

        if t is not None and t.is_alive() and threading.current_thread() is not t:
            t.join(timeout=1.5)

        with self._lock:
            self._thread = None

    def _resolve_device(self, sd) -> tuple[Optional[int], Optional[str]]:
        device_index = self._device_index
        device_name = None

        if device_index is None:
            try:
                default_in = sd.default.device[0]
                if isinstance(default_in, int) and default_in >= 0:
                    device_index = default_in
            except Exception:
                device_index = None

        if device_index is not None:
            try:
                info = sd.query_devices(device_index)
                if isinstance(info, dict):
                    device_name = info.get("name")
            except Exception:
                device_name = None

        return device_index, device_name

    def _run(self) -> None:
        # Local imports to keep text-mode import-safe.
        import queue

        sd = self._sd
        rec = self._rec
        if sd is None or rec is None:
            print("Wake listener missing sd/rec; aborting")
            return

        try:
            sd.query_devices(kind="input")
        except Exception as exc:
            print(f"Wake listener: no input device: {exc}")
            return

        device_index, device_name = self._resolve_device(sd)
        print(f"Wake listener using mic: {device_name} (index {device_index})")

        # 250ms blocks keep latency reasonable and CPU low.
        blocksize = max(256, int(self._sample_rate_hz * 0.25))
        q: "queue.Queue[bytes]" = queue.Queue(maxsize=30)

        def callback(indata, frames, _time, status):  # pragma: no cover
            _ = frames
            _ = _time
            _ = status
            try:
                q.put_nowait(indata.tobytes())
            except Exception:
                # Drop audio if we're falling behind.
                pass

        last_triggered_at = 0.0

        try:
            with sd.InputStream(
                samplerate=self._sample_rate_hz,
                channels=self._channels,
                dtype="int16",
                device=device_index,
                blocksize=blocksize,
                callback=callback,
            ):
                print("Audio stream started")

                while not self._stop.is_set():
                    try:
                        data = q.get(timeout=0.25)
                    except queue.Empty:
                        time.sleep(0.05)
                        continue

                    print("Received audio chunk")

                    triggered = False
                    keyword = ""

                    try:
                        print("Recognizer processing audio")

                        if rec.AcceptWaveform(data):
                            final_raw = rec.Result()
                            print("Final:", final_raw)

                            payload = json.loads(final_raw or "{}")
                            text = (payload.get("text") or "").strip().lower()
                            print(f"Heard: {text}")

                            for p in self._phrases:
                                if p and p in text:
                                    triggered = True
                                    keyword = p
                                    break
                        else:
                            partial_raw = rec.PartialResult()
                            print("Partial:", partial_raw)

                            payload = json.loads(partial_raw or "{}")
                            partial = (payload.get("partial") or "").strip().lower()
                            if partial:
                                print(f"Heard: {partial}")

                            for p in self._phrases:
                                if p and p in partial:
                                    triggered = True
                                    keyword = p
                                    break
                    except Exception as exc:
                        print(f"Wake recognizer error: {exc}")
                        continue

                    if not triggered:
                        continue

                    now = time.monotonic()
                    if self._cooldown_seconds > 0 and (now - last_triggered_at) < self._cooldown_seconds:
                        continue

                    last_triggered_at = now

                    try:
                        rec.Reset()
                    except Exception:
                        pass

                    try:
                        self._on_wake(keyword)
                    except Exception as exc:
                        print(f"Wake callback error: {exc}")
                        pass

        except Exception as exc:
            print(f"Wake listener crashed: {exc}")
            return


"""Microphone input.

Step 3A introduced a one-shot microphone capture path.
Step 3B improved usability and diagnostics.
Step 3D improves perceived responsiveness by stopping early after trailing silence.

Notes:
- Optional dependencies (e.g., `sounddevice`) are imported lazily so text-mode
  runs even if voice deps are not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AudioChunk:
    """Captured audio plus minimal diagnostics.

    `data` is raw PCM16 little-endian.
    """

    data: bytes
    sample_rate_hz: int
    channels: int = 1

    duration_seconds: Optional[float] = None
    device_index: Optional[int] = None
    device_name: Optional[str] = None

    peak: Optional[int] = None
    rms: Optional[float] = None


class MicrophoneError(RuntimeError):
    """Microphone input failure."""


class NoMicrophoneAvailable(MicrophoneError):
    """No usable microphone device is available."""


class NoSpeechDetected(MicrophoneError):
    """Audio was captured but appears too quiet / silent."""


class Microphone:
    """Microphone capture interface."""

    def start(self) -> None:
        raise NotImplementedError

    def read(self) -> Optional[AudioChunk]:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class SoundDeviceMicrophone:
    """One-shot microphone capture using `sounddevice` (PortAudio).

    This implementation is intentionally conservative:
    - records up to `max_seconds`
    - stops early if speech has started and then trailing silence is detected
    """

    def __init__(
        self,
        *,
        sample_rate_hz: int = 16000,
        channels: int = 1,
        min_peak: int = 300,
        device_index: Optional[int] = None,
        trailing_silence_seconds: float = 0.6,
    ) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.min_peak = min_peak
        self.device_index = device_index
        self.trailing_silence_seconds = trailing_silence_seconds

    def _resolve_device(self, sd) -> tuple[Optional[int], Optional[str]]:
        """Return (device_index, device_name) when possible."""

        try:
            # (input, output)
            default_in = sd.default.device[0]
        except Exception:
            default_in = None

        device_index = self.device_index
        if device_index is None and isinstance(default_in, int) and default_in >= 0:
            device_index = default_in

        if device_index is None:
            return None, None

        try:
            info = sd.query_devices(device_index)
            name = info.get("name") if isinstance(info, dict) else None
            return device_index, name
        except Exception:
            return device_index, None

    def record(self, *, max_seconds: float = 5.0) -> AudioChunk:
        """Record a single blocking chunk from the input device."""

        try:
            import sounddevice as sd  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise MicrophoneError(
                "Voice dependencies are not installed. Install `sounddevice` to use voice input."
            ) from exc

        try:
            import numpy as np  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise MicrophoneError("Missing dependency: `numpy`.") from exc

        try:
            sd.query_devices(kind="input")
        except Exception as exc:
            raise NoMicrophoneAvailable("No microphone input device found.") from exc

        if max_seconds <= 0:
            raise MicrophoneError("Invalid recording duration.")

        if self.sample_rate_hz <= 0:
            raise MicrophoneError("Invalid sample rate.")

        if self.channels <= 0:
            raise MicrophoneError("Invalid channel count.")

        device_index, device_name = self._resolve_device(sd)

        # Read in small blocks to allow early stop after trailing silence.
        block_seconds = 0.1
        blocksize = max(256, int(self.sample_rate_hz * block_seconds))

        # After speech starts, consider "silence" as being below this threshold.
        silence_peak = max(1, int(self.min_peak / 3))

        try:
            import queue
            import time

            q: "queue.Queue[np.ndarray]" = queue.Queue()

            def callback(indata, frames, _time, status):  # pragma: no cover
                # Avoid printing; surface via higher-level errors/diagnostics if needed.
                _ = status
                q.put(indata.copy())

            captured: list[np.ndarray] = []
            speech_started = False
            trailing_silence = 0.0

            started_at = time.monotonic()
            with sd.InputStream(
                samplerate=self.sample_rate_hz,
                channels=self.channels,
                dtype="int16",
                device=device_index,
                blocksize=blocksize,
                callback=callback,
            ):
                while True:
                    elapsed = time.monotonic() - started_at
                    if elapsed >= max_seconds:
                        break

                    timeout = min(0.25, max_seconds - elapsed)
                    try:
                        block = q.get(timeout=timeout)
                    except queue.Empty:
                        continue

                    captured.append(block)

                    block_i16 = np.asarray(block, dtype=np.int16)
                    block_peak = int(np.max(np.abs(block_i16))) if block_i16.size else 0

                    if block_peak >= self.min_peak:
                        speech_started = True
                        trailing_silence = 0.0
                    elif speech_started:
                        trailing_silence += block_i16.shape[0] / float(self.sample_rate_hz)
                        if self.trailing_silence_seconds > 0 and trailing_silence >= self.trailing_silence_seconds:
                            break

        except Exception as exc:
            raise MicrophoneError(f"Failed to record audio: {exc}") from exc

        if not captured:
            raise MicrophoneError("Recorded empty audio.")

        audio_i16 = np.concatenate(captured, axis=0).astype(np.int16, copy=False)
        if audio_i16.size == 0:
            raise MicrophoneError("Recorded empty audio.")

        peak = int(np.max(np.abs(audio_i16)))

        audio_f = audio_i16.astype(np.float32)
        rms = float(np.sqrt(np.mean(audio_f * audio_f)))

        duration_seconds = audio_i16.shape[0] / float(self.sample_rate_hz)

        if peak < self.min_peak:
            device_str = (
                f"{device_name} (index {device_index})" if device_name else f"index {device_index}"
            )
            raise NoSpeechDetected(
                "Audio captured but too quiet. "
                f"Device: {device_str}. "
                f"duration={duration_seconds:.2f}s sr={self.sample_rate_hz}Hz peak={peak} rms={rms:.1f}. "
                "Try again closer to the microphone or raise the input level."
            )

        return AudioChunk(
            data=audio_i16.tobytes(),
            sample_rate_hz=self.sample_rate_hz,
            channels=self.channels,
            duration_seconds=duration_seconds,
            device_index=device_index,
            device_name=device_name,
            peak=peak,
            rms=rms,
        )

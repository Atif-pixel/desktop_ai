"""Assistant runtime service.

Step 7: adds a small in-memory session context layer to support safe follow-ups.

Wake word + command mode are coordinated by tray runtime (not by the CLI loop).
"""

from __future__ import annotations

import sys

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from app.brain.orchestrator import Orchestrator
from app.config.settings import Settings
from app.core.enums import IntentType
from app.core.logger import get_logger
from app.core.state import AssistantState
from app.core.types import AssistantRequest, AssistantResponse
from app.input.voice.microphone import (
    MicrophoneError,
    NoMicrophoneAvailable,
    NoSpeechDetected,
    SoundDeviceMicrophone,
)
from app.input.voice.speech_to_text import (
    SpeechNotUnderstood,
    SpeechToText,
    SpeechToTextError,
    Transcript,
    VoskSpeechToText,
)
from app.output.text_to_speech import TextToSpeech, TextToSpeechConfig, default_text_to_speech



class RuntimeIntent(str, Enum):
    """Fixed runtime intents for command-mode handling."""

    OPEN_CHROME = "OPEN_CHROME"
    OPEN_YOUTUBE = "OPEN_YOUTUBE"
    SEARCH_GOOGLE = "SEARCH_GOOGLE"
    PLAY_MUSIC = "PLAY_MUSIC"
    EXIT = "EXIT"
    UNKNOWN = "UNKNOWN"


def _normalize_command(command: str) -> str:
    return " ".join((command or "").strip().lower().split())


def _extract_google_query(command: str) -> str:
    """Extract a Google search query from a user command (best-effort)."""

    text = _normalize_command(command)
    if not text:
        return ""

    prefixes = (
        "search google ",
        "search for ",
        "search ",
        "google ",
        "find ",
        "look up ",
        "lookup ",
    )

    for p in prefixes:
        if text.startswith(p):
            q = text[len(p) :].strip()
            # Trim common trailing filler.
            q = q.removesuffix(" on google").strip() if hasattr(q, "removesuffix") else q
            return q

    # e.g. "look up python" (no space variant)
    if text.startswith("lookup") and len(text) > len("lookup"):
        return text[len("lookup") :].strip()

    return ""


def detect_intent(command: str) -> RuntimeIntent:
    """Detect a fixed runtime intent from free-form text."""

    text = _normalize_command(command)
    if not text:
        return RuntimeIntent.UNKNOWN

    # Exit intent
    if text in {"exit", "quit", "stop", "stop jarvis"}:
        return RuntimeIntent.EXIT

    # Search intent
    if text.startswith(("search ", "google ", "find ", "look up ", "lookup ")):
        return RuntimeIntent.SEARCH_GOOGLE

    # YouTube
    if "youtube" in text:
        if any(w in text for w in ("open", "watch", "launch")) or text == "youtube":
            return RuntimeIntent.OPEN_YOUTUBE

    # Chrome / browser
    if "chrome" in text or "browser" in text:
        if any(w in text for w in ("open", "launch")) or text in {"chrome", "browser"}:
            return RuntimeIntent.OPEN_CHROME

    # Music
    if any(w in text for w in ("music", "song", "play music")):
        return RuntimeIntent.PLAY_MUSIC

    return RuntimeIntent.UNKNOWN
@dataclass(frozen=True)
class VoiceListenResult:
    """Result of one-shot voice capture + transcription."""

    ok: bool
    transcript: Optional[Transcript] = None
    error: Optional[str] = None
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class AssistantRuntime:
    """High-level runtime wiring for the assistant."""

    def __init__(
        self,
        orchestrator: Optional[Orchestrator] = None,
        *,
        settings: Optional[Settings] = None,
        microphone: Optional[SoundDeviceMicrophone] = None,
        speech_to_text: Optional[SpeechToText] = None,
        text_to_speech: Optional[TextToSpeech] = None,
    ) -> None:
        self._orchestrator = orchestrator or Orchestrator()
        self.settings = settings or Settings()
        self.state = AssistantState()
        self._log = get_logger(__name__)

        # One-time wake activation flag (tray mode coordinates behavior).
        self.wake_mode = True

        self._microphone = microphone or SoundDeviceMicrophone(
            sample_rate_hz=self.settings.voice_sample_rate_hz,
            channels=self.settings.voice_channels,
            min_peak=self.settings.voice_min_peak,
            device_index=self.settings.voice_device_index,
            trailing_silence_seconds=self.settings.voice_trailing_silence_seconds,
        )
        self._speech_to_text = speech_to_text or VoskSpeechToText()

        tts_cfg = TextToSpeechConfig(enabled=self.settings.tts_enabled, rate=self.settings.tts_rate)
        self._text_to_speech = text_to_speech or default_text_to_speech(tts_cfg)

    def process_text(self, text: str) -> AssistantResponse:
        """Process already-transcribed text."""

        self.state.last_user_text = text

        request = AssistantRequest(
            text=text,
            metadata={"session": self.state.session_context()},
        )

        response = self._orchestrator.handle(request)
        self._update_session_state(response)
        return response

    def process_command(self, command: str) -> AssistantResponse:
        """Process a command using fixed runtime intents.

        This keeps detection logic separate from execution logic.
        """

        intent = detect_intent(command)

        if intent == RuntimeIntent.OPEN_CHROME:
            return self.process_text("open chrome")

        if intent == RuntimeIntent.OPEN_YOUTUBE:
            return self.process_text("open youtube")

        if intent == RuntimeIntent.SEARCH_GOOGLE:
            query = _extract_google_query(command)
            if not query:
                return AssistantResponse(text="What should I search for?")
            return self.process_text(f"search google {query}")

        if intent == RuntimeIntent.PLAY_MUSIC:
            # Safe starter behavior: open YouTube search for "music".
            return self.process_text("search youtube music")

        if intent == RuntimeIntent.EXIT:
            return AssistantResponse(text="Goodbye.")

        return AssistantResponse(text="Sorry, I didn't understand that.")

    def _update_session_state(self, response: AssistantResponse) -> None:
        md = response.metadata if isinstance(response.metadata, dict) else {}

        intent_type = md.get("intent_type")
        if isinstance(intent_type, str):
            try:
                self.state.last_intent = IntentType(intent_type)
            except Exception:
                self.state.last_intent = IntentType.UNKNOWN

        entities = md.get("intent_entities")
        self.state.last_intent_entities = entities if isinstance(entities, dict) else {}

        action_area = md.get("action_area")
        self.state.last_action_area = action_area if isinstance(action_area, str) else ""

        result = response.result
        data = result.data if (result is not None and isinstance(result.data, dict)) else {}

        # Record last successful open/search targets for follow-ups.
        if result is not None and result.ok and result.executed:
            app = data.get("app")
            if isinstance(app, str) and app.strip():
                self.state.last_open_app = app.strip().lower()

            site = data.get("site")
            if isinstance(site, str) and site.strip():
                self.state.last_browser_site = site.strip().lower()

            engine = data.get("engine")
            query = data.get("query")
            if isinstance(engine, str) and engine.strip() and isinstance(query, str) and query.strip():
                self.state.last_search_engine = engine.strip().lower()
                self.state.last_search_query = query.strip()

            target = data.get("target")
            if isinstance(target, str) and target.strip():
                self.state.last_file_target = target.strip().lower()

    @staticmethod
    def _one_line_error(exc: Exception) -> str:
        msg = str(exc).strip() or exc.__class__.__name__
        return " ".join(msg.split())

    def speak_text(self, text: str) -> None:
        """Speak text using the configured TTS backend (failure-safe)."""

        try:
            self._text_to_speech.speak(text)
        except Exception as exc:  # pragma: no cover
            msg = self._one_line_error(exc)
            print(f"TTS failed: {msg}", file=sys.stderr)
            self._log.debug("TTS failed: %s", msg)
            return None

    def speak_response(self, response: AssistantResponse) -> None:
        """Speak an assistant response (failure-safe).

        Step 5C: avoid speaking the full global help text.
        """

        result = response.result
        data = result.data if result is not None else {}
        if isinstance(data, dict) and data.get("builtin") == "help":
            section = data.get("section")
            if isinstance(section, str) and section.strip():
                return self.speak_text(response.text)

            return self.speak_text(
                "I displayed the available commands on screen. "
                "Say app help, browser help, system help, or file help for a shorter list."
            )

        return self.speak_text(response.text)

    def greet_user(self) -> None:
        """Speak a short greeting with the current local time.

        Intended for wake-word triggers only (tray mode).
        """

        from datetime import datetime

        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        greeting = f"Hey sir, current time is {time_str}"
        self.speak_response(AssistantResponse(text=greeting))

    def run_continuous_listener(self) -> None:
        """Command mode: keep listening without wake word.

        Uses repeated one-shot listens (no continuous audio transcription) until an exit keyword is heard.
        """

        print("Command mode: listening for commands. Say 'exit' or 'stop jarvis' to stop.")

        while True:
            try:
                listen = self.listen_once()
            except Exception as exc:
                print(f"Continuous listener error: {exc}")
                continue

            if not listen.ok or not listen.transcript:
                if listen.error:
                    print(f"Voice error: {listen.error}")
                continue

            command = (listen.transcript.text or "").strip()
            if not command:
                continue

            print(f"Command: {command}")

            intent = detect_intent(command)
            if intent == RuntimeIntent.EXIT:
                self.speak_text("Goodbye.")
                break

            try:
                response = self.process_command(command)
                self.speak_response(response)
            except Exception as exc:
                print(f"Command processing error: {exc}")

    def listen_once(self) -> VoiceListenResult:
        """Capture and transcribe one utterance (no assistant processing)."""

        diagnostics: Dict[str, Any] = {
            "max_seconds": self.settings.voice_max_seconds,
        }

        try:
            chunk = self._microphone.record(max_seconds=self.settings.voice_max_seconds)
            diagnostics.update(
                {
                    "device_index": chunk.device_index,
                    "device_name": chunk.device_name,
                    "duration_seconds": chunk.duration_seconds,
                    "sample_rate_hz": chunk.sample_rate_hz,
                    "channels": chunk.channels,
                    "peak": chunk.peak,
                    "rms": chunk.rms,
                }
            )

            transcript = self._speech_to_text.transcribe(chunk)
            diagnostics["stt_confidence"] = transcript.confidence

            return VoiceListenResult(ok=True, transcript=transcript, diagnostics=diagnostics)
        except NoMicrophoneAvailable as exc:
            return VoiceListenResult(ok=False, error=str(exc), diagnostics=diagnostics)
        except NoSpeechDetected as exc:
            return VoiceListenResult(ok=False, error=str(exc), diagnostics=diagnostics)
        except SpeechNotUnderstood as exc:
            return VoiceListenResult(ok=False, error=str(exc), diagnostics=diagnostics)
        except (MicrophoneError, SpeechToTextError) as exc:
            return VoiceListenResult(ok=False, error=f"Voice input failed: {exc}", diagnostics=diagnostics)
        except Exception as exc:  # pragma: no cover
            return VoiceListenResult(
                ok=False,
                error=f"Voice input failed unexpectedly: {exc}",
                diagnostics=diagnostics,
            )

    def process_voice_once(self) -> AssistantResponse:
        """Capture + transcribe one utterance, then run the normal pipeline."""

        listen = self.listen_once()
        if not listen.ok or not listen.transcript:
            return AssistantResponse(text=listen.error or "Voice input failed.", metadata=listen.diagnostics)

        response = self.process_text(listen.transcript.text)
        metadata = dict(response.metadata)
        metadata.update(listen.diagnostics)
        metadata["transcript"] = listen.transcript.text
        metadata["stt_confidence"] = listen.transcript.confidence
        return AssistantResponse(text=response.text, result=response.result, metadata=metadata)


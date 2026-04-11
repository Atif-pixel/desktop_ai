"""Assistant runtime service.

Step 7: adds a small in-memory session context layer to support safe follow-ups.

This does NOT add wakeword support or continuous listening.
"""

from __future__ import annotations

import sys

from dataclasses import dataclass, field
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



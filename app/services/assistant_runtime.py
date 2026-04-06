"""Assistant runtime service.

Step 3A added a controlled, one-shot voice input path.
Step 3B improves debuggability and usability while keeping the architecture intact.

This does NOT add wakeword support or continuous listening.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.brain.orchestrator import Orchestrator
from app.config.settings import Settings
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
    ) -> None:
        self._orchestrator = orchestrator or Orchestrator()
        self.settings = settings or Settings()
        self.state = AssistantState()

        self._microphone = microphone or SoundDeviceMicrophone(
            sample_rate_hz=self.settings.voice_sample_rate_hz,
            channels=self.settings.voice_channels,
            min_peak=self.settings.voice_min_peak,
            device_index=self.settings.voice_device_index,
            trailing_silence_seconds=self.settings.voice_trailing_silence_seconds,
        )
        self._speech_to_text = speech_to_text or VoskSpeechToText()

    def process_text(self, text: str) -> AssistantResponse:
        """Process already-transcribed text."""

        self.state.last_user_text = text
        request = AssistantRequest(text=text)
        return self._orchestrator.handle(request)

    def listen_once(self) -> VoiceListenResult:
        """Capture and transcribe one utterance (no assistant processing)."""

        diagnostics: Dict[str, Any] = {
            "max_seconds": self.settings.voice_max_seconds,
        }

        chunk = None
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
            # Distinct from microphone failures: audio was captured but STT produced no text.
            return VoiceListenResult(ok=False, error=str(exc), diagnostics=diagnostics)
        except (MicrophoneError, SpeechToTextError) as exc:
            return VoiceListenResult(ok=False, error=f"Voice input failed: {exc}", diagnostics=diagnostics)
        except Exception as exc:  # pragma: no cover
            return VoiceListenResult(
                ok=False, error=f"Voice input failed unexpectedly: {exc}", diagnostics=diagnostics
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


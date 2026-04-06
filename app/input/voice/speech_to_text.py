"""Speech-to-text interface.

Step 2B defines a minimal contract. Implementation (Whisper, Windows APIs, etc.)
will be added later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .microphone import AudioChunk


@dataclass(frozen=True)
class Transcript:
    """Speech-to-text output."""

    text: str
    confidence: Optional[float] = None


class SpeechToText:
    """Transcribe captured audio into text (placeholder)."""

    def transcribe(self, chunk: AudioChunk) -> Transcript:
        raise NotImplementedError

"""Microphone input abstraction.

Voice-first design: this module will own microphone capture concerns.
Step 2B provides only the interface/skeleton.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AudioChunk:
    """A small unit of captured audio.

    Representation is intentionally unspecified in Step 2B.
    """

    data: bytes
    sample_rate_hz: int


class Microphone:
    """Microphone capture interface (placeholder)."""

    def start(self) -> None:
        """Start capturing audio."""

        raise NotImplementedError

    def read(self) -> Optional[AudioChunk]:
        """Read the next available audio chunk, or None if none is available."""

        raise NotImplementedError

    def stop(self) -> None:
        """Stop capturing audio."""

        raise NotImplementedError

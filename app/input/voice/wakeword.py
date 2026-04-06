"""Wakeword detection interface.

Wakeword can be implemented as text-based (post-STT) or audio-based.
Step 2B keeps this as a small contract.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WakewordMatch:
    matched: bool
    keyword: str = ""


class WakewordDetector:
    """Detect wakeword in a transcript (placeholder)."""

    def detect(self, text: str) -> WakewordMatch:
        raise NotImplementedError

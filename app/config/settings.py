"""Settings model.

Step 3B adds a small set of voice tuning values for one-shot microphone input.
Step 3D adds a trailing-silence setting to reduce perceived delay.

Loading from env/files is still deferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .constants import DEFAULT_LANGUAGE, DEFAULT_WAKEWORD


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the assistant."""

    language: str = DEFAULT_LANGUAGE
    wakeword: str = DEFAULT_WAKEWORD

    # One-shot voice capture tuning (used by `AssistantRuntime`).
    voice_max_seconds: float = 5.0
    voice_sample_rate_hz: int = 16000
    voice_channels: int = 1
    voice_min_peak: int = 300
    voice_device_index: Optional[int] = None
    voice_trailing_silence_seconds: float = 0.6

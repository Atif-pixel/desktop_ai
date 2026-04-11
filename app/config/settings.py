"""Settings model.

Step 3B adds a small set of voice tuning values for one-shot microphone input.
Step 3D adds a trailing-silence setting to reduce perceived delay.
Step 4 adds basic TTS output settings.
Step 5A adds an optional hotkey trigger configuration.
Step 10 adds an optional lightweight wake word trigger (tray mode only).

Loading from env/files is still deferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

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

    # Voice UX (terminal): keep normal output clean.
    voice_show_diagnostics: bool = False

    # Text-to-speech output (Step 4).
    tts_enabled: bool = True
    tts_rate: int = 0

    # Hotkey trigger for one-shot voice input (Step 5A).
    # Requires the optional `keyboard` dependency.
    hotkey_enabled: bool = True
    hotkey_combo: str = "shift+v"

    # Wake word trigger (Step 10).
    # Designed to be enabled only in tray/background mode.
    wake_word_enabled: bool = False
    wake_word_phrases: Tuple[str, ...] = ("hey jarvis", "jarvis")

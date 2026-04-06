"""Core enums used across the assistant.

These are intentionally small and stable to keep modules loosely coupled.
"""

from __future__ import annotations

from enum import Enum


class IntentType(str, Enum):
    """High-level intent categories for routing."""

    UNKNOWN = "unknown"
    CHAT = "chat"

    SYSTEM = "system"
    TIME = "time"

    APP = "app"
    BROWSER = "browser"
    FILE = "file"

    EXIT = "exit"

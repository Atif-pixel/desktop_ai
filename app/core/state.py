"""Assistant state container.

This is a minimal mutable state object to support future background runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import IntentType


@dataclass
class AssistantState:
    """Mutable assistant state for the running session."""

    is_listening: bool = False
    last_user_text: str = ""
    last_intent: IntentType = IntentType.UNKNOWN

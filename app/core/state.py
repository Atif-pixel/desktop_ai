"""Assistant state container.

Small mutable state for the running session.

Step 7: expand state to support a minimal short-term session context layer for
safe follow-up commands ("it", "that", "again").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .enums import IntentType


@dataclass
class AssistantState:
    """Mutable assistant state for the running session."""

    is_listening: bool = False

    last_user_text: str = ""
    last_intent: IntentType = IntentType.UNKNOWN
    last_intent_entities: Dict[str, Any] = field(default_factory=dict)
    last_action_area: str = ""

    last_open_app: str = ""

    last_browser_site: str = ""
    last_search_engine: str = ""
    last_search_query: str = ""

    last_file_target: str = ""

    def session_context(self) -> Dict[str, Any]:
        """Return a small context dict for follow-up parsing.

        Keep this minimal and deterministic.
        """

        return {
            "last_open_app": self.last_open_app or None,
            "last_browser_site": self.last_browser_site or None,
            "last_search_engine": self.last_search_engine or None,
            "last_search_query": self.last_search_query or None,
            "last_file_target": self.last_file_target or None,
        }

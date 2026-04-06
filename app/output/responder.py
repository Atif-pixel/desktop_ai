"""Response construction.

Step 2B: produce a structured `AssistantResponse` from intent + action result.
"""

from __future__ import annotations

from app.core.types import AssistantResponse, CommandResult, ParsedIntent


class Responder:
    """Build user-facing responses (placeholder)."""

    def build(self, intent: ParsedIntent, result: CommandResult) -> AssistantResponse:
        if result.ok:
            text = result.message or "OK"
        else:
            text = result.message or "Sorry, I couldn't do that yet."

        return AssistantResponse(text=text, result=result)

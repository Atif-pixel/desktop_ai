"""Assistant runtime service (placeholder).

Step 2B: defines the object that will later own the background loop,
voice capture, wakeword, and orchestrator integration.

Not runnable yet by design.
"""

from __future__ import annotations

from typing import Optional

from app.brain.orchestrator import Orchestrator
from app.core.state import AssistantState
from app.core.types import AssistantRequest, AssistantResponse


class AssistantRuntime:
    """High-level runtime wiring for the assistant (placeholder)."""

    def __init__(self, orchestrator: Optional[Orchestrator] = None) -> None:
        self._orchestrator = orchestrator or Orchestrator()
        self.state = AssistantState()

    def process_text(self, text: str) -> AssistantResponse:
        """Process already-transcribed text.

        Voice capture/STT will later feed into this.
        """

        self.state.last_user_text = text
        request = AssistantRequest(text=text)
        response = self._orchestrator.handle(request)
        return response


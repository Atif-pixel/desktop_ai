"""Orchestrator (brain).

Voice-first flow (Step 2B skeleton):
request -> intent_parser -> command_router -> responder -> response

No runtime loop and no OS execution in Step 2B.
"""

from __future__ import annotations

from typing import Optional

from app.brain.command_router import CommandRouter
from app.brain.intent_parser import IntentParser
from app.core.types import AssistantRequest, AssistantResponse
from app.output.responder import Responder


class Orchestrator:
    """Coordinate parsing, routing, and response building (placeholder)."""

    def __init__(
        self,
        intent_parser: Optional[IntentParser] = None,
        command_router: Optional[CommandRouter] = None,
        responder: Optional[Responder] = None,
    ) -> None:
        self._intent_parser = intent_parser or IntentParser()
        self._command_router = command_router or CommandRouter()
        self._responder = responder or Responder()

    def handle(self, request: AssistantRequest) -> AssistantResponse:
        intent = self._intent_parser.parse(request)
        result = self._command_router.route(intent)
        return self._responder.build(intent=intent, result=result)


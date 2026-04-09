"""Orchestrator (brain).

Voice-first flow:
request -> intent_parser -> command_router -> responder -> response

Step 7: attach minimal metadata to responses so the runtime can update its
session state without changing the overall architecture.
"""

from __future__ import annotations

from typing import Optional

from app.brain.command_router import CommandRouter
from app.brain.intent_parser import IntentParser
from app.core.types import AssistantRequest, AssistantResponse
from app.output.responder import Responder


class Orchestrator:
    """Coordinate parsing, routing, and response building."""

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
        response = self._responder.build(intent=intent, result=result)

        metadata = dict(response.metadata)
        metadata.update(
            {
                "intent_type": intent.intent_type.value,
                "intent_raw_text": intent.raw_text,
                "intent_entities": dict(intent.entities or {}),
                "action_area": intent.intent_type.value,
            }
        )

        return AssistantResponse(text=response.text, result=response.result, metadata=metadata)

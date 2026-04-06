"""Core data models for request/response plumbing.

Step 2B goal: provide minimal, practical structures for voice-first flow:
input -> intent -> orchestrator -> action -> response.

No heavy logic here; these are shared types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .enums import IntentType


@dataclass(frozen=True)
class AssistantRequest:
    """Normalized inbound request into the assistant.

    Voice-first: `text` is typically produced by speech-to-text.
    `audio` is reserved for future direct-audio intent/wakeword pipelines.
    """

    text: Optional[str] = None
    audio: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedIntent:
    """Internal intent representation used by the brain layer."""

    intent_type: IntentType = IntentType.UNKNOWN
    raw_text: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandResult:
    """Result of attempting an action.

    Step 2B: actions should *not* execute real OS commands yet.
    Use this to return structured placeholders that will later drive execution.
    """

    ok: bool
    executed: bool = False
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantResponse:
    """Structured response returned to output layer (text, later TTS)."""

    text: str
    result: Optional[CommandResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

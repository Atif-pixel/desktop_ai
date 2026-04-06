"""Intent parsing.

Step 2D: deterministic, rule-based parsing for a small, useful command set.

Goals:
- Keep parsing simple and maintainable
- No LLM/agent behavior
- Support text-mode commands that later map cleanly to voice transcripts
"""

from __future__ import annotations

from app.core.enums import IntentType
from app.core.types import AssistantRequest, ParsedIntent


_EXIT_WORDS = {"exit", "quit", "stop"}


class IntentParser:
    """Parse raw request text into a coarse intent type."""

    def parse(self, request: AssistantRequest) -> ParsedIntent:
        raw_text = (request.text or "").strip()
        lowered = raw_text.lower()

        if not lowered:
            return ParsedIntent(intent_type=IntentType.UNKNOWN, raw_text="")

        if lowered in {"help", "?", "h"}:
            return ParsedIntent(
                intent_type=IntentType.CHAT,
                raw_text=raw_text,
                entities={"builtin": "help"},
            )

        if lowered in {"hi", "hello", "hey"}:
            return ParsedIntent(
                intent_type=IntentType.CHAT,
                raw_text=raw_text,
                entities={"builtin": "greet"},
            )

        if lowered in _EXIT_WORDS:
            return ParsedIntent(
                intent_type=IntentType.EXIT,
                raw_text=raw_text,
                entities={"builtin": "exit"},
            )

        if lowered == "time" or lowered.startswith("what time") or lowered.startswith("what's the time"):
            return ParsedIntent(
                intent_type=IntentType.TIME,
                raw_text=raw_text,
                entities={"builtin": "time"},
            )

        # Explicit category prefixes keep routing obvious and debuggable.
        for prefix, intent_type in (
            ("system ", IntentType.SYSTEM),
            ("app ", IntentType.APP),
            ("browser ", IntentType.BROWSER),
            ("file ", IntentType.FILE),
        ):
            if lowered.startswith(prefix):
                return ParsedIntent(
                    intent_type=intent_type,
                    raw_text=raw_text,
                    entities={"command": raw_text[len(prefix) :].strip()},
                )

        # Convenience commands.
        if lowered.startswith("open "):
            return ParsedIntent(
                intent_type=IntentType.APP,
                raw_text=raw_text,
                entities={"command": raw_text[len("open ") :].strip()},
            )

        if lowered.startswith("search "):
            return ParsedIntent(
                intent_type=IntentType.BROWSER,
                raw_text=raw_text,
                entities={"query": raw_text[len("search ") :].strip()},
            )

        return ParsedIntent(intent_type=IntentType.UNKNOWN, raw_text=raw_text)

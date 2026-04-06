"""Intent parsing.

Deterministic, rule-based parsing for a small, useful command set.

Step 3D improves spoken-phrase tolerance by normalizing text before matching.
This is still intentionally *not* full NLP.
"""

from __future__ import annotations

import re

from app.core.enums import IntentType
from app.core.types import AssistantRequest, ParsedIntent


_EXIT_WORDS = {"exit", "quit", "stop"}
_GREET_WORDS = {"hi", "hello", "hey"}
_ASSISTANT_NAMES = {"jarvis", "assistant"}


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_punctuation(text: str) -> str:
    # Keep letters/numbers/spaces; convert punctuation to spaces.
    return re.sub(r"[^a-z0-9\s]", " ", text)


def _dedupe_consecutive_tokens(tokens: list[str]) -> list[str]:
    if not tokens:
        return tokens

    out = [tokens[0]]
    for t in tokens[1:]:
        if t != out[-1]:
            out.append(t)
    return out


def _normalize_for_intent(text: str) -> str:
    lowered = text.lower()
    lowered = _strip_punctuation(lowered)
    lowered = _collapse_spaces(lowered)

    if not lowered:
        return ""

    tokens = lowered.split(" ")

    # Remove assistant name if user says "hi jarvis" / "jarvis ...".
    if tokens and tokens[0] in _ASSISTANT_NAMES:
        tokens = tokens[1:]

    # Drop trailing polite filler.
    while tokens and tokens[-1] in {"please", "thanks", "thank", "you"}:
        tokens = tokens[:-1]

    # Drop leading polite filler.
    while tokens and tokens[0] in {"please", "hey", "ok", "okay"}:
        tokens = tokens[1:]

    tokens = _dedupe_consecutive_tokens(tokens)

    # Collapse repeated greeting sequences at the start: "hello hello" -> "hello".
    if tokens and tokens[0] in _GREET_WORDS:
        while len(tokens) > 1 and tokens[1] in _GREET_WORDS:
            tokens.pop(1)

        # "hi jarvis" -> treat as greeting; remove assistant name.
        if len(tokens) > 1 and tokens[1] in _ASSISTANT_NAMES:
            tokens = tokens[:1]

    return " ".join(tokens)


def _strip_leading_request_phrases(text: str) -> str:
    # Very small set of spoken prefixes.
    prefixes = (
        "can you ",
        "could you ",
        "would you ",
        "please ",
        "hey ",
    )

    out = text
    while True:
        changed = False
        for p in prefixes:
            if out.startswith(p):
                out = out[len(p) :].lstrip()
                changed = True
        if not changed:
            break

    return out


class IntentParser:
    """Parse raw request text into a coarse intent type."""

    def parse(self, request: AssistantRequest) -> ParsedIntent:
        raw_text = (request.text or "").strip()

        # Keep legacy '?' help behavior for text-mode.
        if raw_text == "?":
            return ParsedIntent(
                intent_type=IntentType.CHAT,
                raw_text=raw_text,
                entities={"builtin": "help"},
            )

        normalized = _normalize_for_intent(raw_text)

        if not normalized:
            return ParsedIntent(intent_type=IntentType.UNKNOWN, raw_text="")

        normalized = _strip_leading_request_phrases(normalized)

        if normalized in {"help", "h"} or normalized.startswith("help "):
            return ParsedIntent(
                intent_type=IntentType.CHAT,
                raw_text=raw_text,
                entities={"builtin": "help"},
            )

        if normalized in _GREET_WORDS:
            return ParsedIntent(
                intent_type=IntentType.CHAT,
                raw_text=raw_text,
                entities={"builtin": "greet"},
            )

        if normalized in _EXIT_WORDS:
            return ParsedIntent(
                intent_type=IntentType.EXIT,
                raw_text=raw_text,
                entities={"builtin": "exit"},
            )

        if (
            normalized == "time"
            or normalized.startswith("what time")
            or normalized.startswith("whats the time")
            or normalized.startswith("what is the time")
            or normalized.endswith(" time")
        ):
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
            if normalized.startswith(prefix):
                return ParsedIntent(
                    intent_type=intent_type,
                    raw_text=raw_text,
                    entities={"command": normalized[len(prefix) :].strip()},
                )

        tokens = normalized.split(" ")

        # Open command can appear inside a spoken request, e.g. "can you open chrome".
        if "open" in tokens:
            idx = tokens.index("open")
            rest = tokens[idx + 1 :]
            # Remove simple articles: "open the calculator".
            if rest and rest[0] in {"the", "a", "an"}:
                rest = rest[1:]

            if rest:
                cmd = " ".join(rest).strip()
                # Normalize common short forms.
                if cmd in {"calc", "calculator"}:
                    cmd = "calculator"
                if cmd in {"google chrome"}:
                    cmd = "chrome"

                return ParsedIntent(
                    intent_type=IntentType.APP,
                    raw_text=raw_text,
                    entities={"command": cmd},
                )

        # Search command: "search cats" / "search for cats".
        if "search" in tokens:
            idx = tokens.index("search")
            rest = tokens[idx + 1 :]
            if rest and rest[0] == "for":
                rest = rest[1:]

            query = " ".join(rest).strip()
            if query:
                return ParsedIntent(
                    intent_type=IntentType.BROWSER,
                    raw_text=raw_text,
                    entities={"query": query},
                )

        return ParsedIntent(intent_type=IntentType.UNKNOWN, raw_text=raw_text)

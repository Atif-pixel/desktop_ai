"""Intent parsing.

Deterministic, rule-based parsing for a small, useful command set.

Step 3D improves spoken-phrase tolerance by normalizing text before matching.
Step 5B expands rule coverage for a larger safe command set.

This is still intentionally *not* full NLP.
"""

from __future__ import annotations

import re

from app.core.enums import IntentType
from app.core.types import AssistantRequest, ParsedIntent


_EXIT_WORDS = {"exit", "quit", "stop"}
_GREET_WORDS = {"hi", "hello", "hey"}
_ASSISTANT_NAMES = {"jarvis", "assistant"}

_BROWSER_SITES = {
    "youtube": "youtube",
    "gmail": "gmail",
}

_FILE_TARGETS = {
    "downloads": "downloads",
    "download": "downloads",
    "desktop": "desktop",
}

_APP_ALIASES = {
    "calc": "calculator",
    "calculator": "calculator",
    "google chrome": "chrome",
    "chrome": "chrome",
    "file explorer": "explorer",
    "explorer": "explorer",
    "windows explorer": "explorer",
    "vs code": "vscode",
    "vscode": "vscode",
    "visual studio code": "vscode",
    "settings": "settings",
    "windows settings": "settings",
}

_VOLUME_PHRASES = {
    "volume up": "volume_up",
    "increase volume": "volume_up",
    "volume down": "volume_down",
    "decrease volume": "volume_down",
    "mute": "mute",
    "unmute": "unmute",
}


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
        "hey buddy ",
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


def _normalize_open_target(text: str) -> str:
    # Normalize some common multi-word targets first.
    t = _collapse_spaces(text)

    # Spoken variants: "open downloads folder" / "open the desktop folder".
    if t.endswith(" folder"):
        t = t[:-7].strip()

    return _APP_ALIASES.get(t, t)


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
            section = None
            if normalized.startswith("help "):
                rest = normalized[len("help ") :].strip()
                if rest in {"app", "browser", "system", "file"}:
                    section = rest

            entities = {"builtin": "help"}
            if section:
                entities["section"] = section

            return ParsedIntent(
                intent_type=IntentType.CHAT,
                raw_text=raw_text,
                entities=entities,
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

        if normalized == "date" or normalized.startswith("what date") or normalized.endswith(" date"):
            return ParsedIntent(
                intent_type=IntentType.SYSTEM,
                raw_text=raw_text,
                entities={"command": "date"},
            )

        if (
            normalized in {"what day is it", "what day is today", "day"}
            or normalized.startswith("what day")
            or normalized.endswith(" day")
        ):
            return ParsedIntent(
                intent_type=IntentType.SYSTEM,
                raw_text=raw_text,
                entities={"command": "day"},
            )

        if normalized in _VOLUME_PHRASES:
            return ParsedIntent(
                intent_type=IntentType.SYSTEM,
                raw_text=raw_text,
                entities={"command": _VOLUME_PHRASES[normalized]},
            )


        # Section help: "app help" / "browser help" / "system help" / "file help".
        if normalized.endswith(" help"):
            parts = normalized.split(" ")
            if len(parts) == 2 and parts[1] == "help" and parts[0] in {"app", "browser", "system", "file"}:
                return ParsedIntent(
                    intent_type=IntentType.CHAT,
                    raw_text=raw_text,
                    entities={"builtin": "help", "section": parts[0]},
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

        # Direct site names.
        if normalized in _BROWSER_SITES:
            return ParsedIntent(
                intent_type=IntentType.BROWSER,
                raw_text=raw_text,
                entities={"site": _BROWSER_SITES[normalized]},
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
                cmd_raw = " ".join(rest).strip()
                cmd = _normalize_open_target(cmd_raw)

                # Some open targets are better represented as browser actions.
                if cmd in _BROWSER_SITES:
                    return ParsedIntent(
                        intent_type=IntentType.BROWSER,
                        raw_text=raw_text,
                        entities={"site": _BROWSER_SITES[cmd]},
                    )

                # Some open targets are safe file navigation.
                if cmd in _FILE_TARGETS:
                    return ParsedIntent(
                        intent_type=IntentType.FILE,
                        raw_text=raw_text,
                        entities={"target": _FILE_TARGETS[cmd]},
                    )

                return ParsedIntent(
                    intent_type=IntentType.APP,
                    raw_text=raw_text,
                    entities={"command": cmd},
                )

        # Search command: "search cats" / "search youtube cats" / "search google cats".
        if "search" in tokens:
            idx = tokens.index("search")
            rest = tokens[idx + 1 :]
            if rest and rest[0] == "for":
                rest = rest[1:]

            engine = "google"
            if rest and rest[0] in {"youtube", "yt"}:
                engine = "youtube"
                rest = rest[1:]
            elif rest and rest[0] == "google":
                engine = "google"
                rest = rest[1:]

            query = " ".join(rest).strip()
            if query:
                return ParsedIntent(
                    intent_type=IntentType.BROWSER,
                    raw_text=raw_text,
                    entities={"engine": engine, "query": query},
                )

        return ParsedIntent(intent_type=IntentType.UNKNOWN, raw_text=raw_text)




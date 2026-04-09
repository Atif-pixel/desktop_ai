"""Intent parsing.

Deterministic, rule-based parsing.

Step 7 adds a minimal session-context aware follow-up layer to support safe
references like "it" / "that" / "again".

This remains intentionally *not* full NLP.
"""

from __future__ import annotations

import re
from typing import Any, Dict

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

_REF_WORDS = {"it", "that", "this"}


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


def _normalize_open_target(text: str) -> str:
    t = _collapse_spaces(text)

    # Spoken variants: "open downloads folder" / "open the desktop folder".
    if t.endswith(" folder"):
        t = t[:-7].strip()

    return _APP_ALIASES.get(t, t)


def _session_ctx(request: AssistantRequest) -> Dict[str, Any]:
    md = request.metadata if isinstance(request.metadata, dict) else {}
    ctx = md.get("session")
    return ctx if isinstance(ctx, dict) else {}


def _ctx_str(ctx: Dict[str, Any], key: str) -> str:
    v = ctx.get(key)
    return v.strip() if isinstance(v, str) else ""


def _clarify(raw_text: str, message: str) -> ParsedIntent:
    return ParsedIntent(
        intent_type=IntentType.CHAT,
        raw_text=raw_text,
        entities={"builtin": "clarify", "message": message},
    )


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
        ctx = _session_ctx(request)

        # Help and section help.
        if normalized in {"help", "h"} or normalized.startswith("help "):
            section = None
            if normalized.startswith("help "):
                rest = normalized[len("help ") :].strip()
                if rest in {"app", "browser", "system", "file"}:
                    section = rest

            entities = {"builtin": "help"}
            if section:
                entities["section"] = section

            return ParsedIntent(intent_type=IntentType.CHAT, raw_text=raw_text, entities=entities)

        if normalized.endswith(" help"):
            parts = normalized.split(" ")
            if len(parts) == 2 and parts[1] == "help" and parts[0] in {"app", "browser", "system", "file"}:
                return ParsedIntent(
                    intent_type=IntentType.CHAT,
                    raw_text=raw_text,
                    entities={"builtin": "help", "section": parts[0]},
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

        # Explicit category prefixes.
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

        # Follow-up: "do that on youtube" / "do it on youtube".
        if normalized.startswith("do ") and normalized.endswith(" on youtube"):
            mid = normalized[len("do ") : -len(" on youtube")].strip()
            if mid in _REF_WORDS:
                last_query = _ctx_str(ctx, "last_search_query")
                if not last_query:
                    return _clarify(raw_text, "I'm not sure what 'that' refers to. Please say what to search.")
                return ParsedIntent(
                    intent_type=IntentType.BROWSER,
                    raw_text=raw_text,
                    entities={"engine": "youtube", "query": last_query},
                )

        # Open command.
        if "open" in tokens:
            idx = tokens.index("open")
            rest = tokens[idx + 1 :]
            if rest and rest[0] in {"the", "a", "an"}:
                rest = rest[1:]

            if rest:
                cmd_raw = " ".join(rest).strip()

                # Follow-up: "open it" / "open it again".
                if cmd_raw in {"it", "it again", "that", "that again"}:
                    last_app = _ctx_str(ctx, "last_open_app")
                    if not last_app:
                        return _clarify(raw_text, "I'm not sure what 'it' refers to. Please say the app name.")
                    cmd = last_app
                else:
                    cmd = _normalize_open_target(cmd_raw)

                if cmd in _BROWSER_SITES:
                    return ParsedIntent(
                        intent_type=IntentType.BROWSER,
                        raw_text=raw_text,
                        entities={"site": _BROWSER_SITES[cmd]},
                    )

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

        # Search command.
        if "search" in tokens or normalized.startswith("search "):
            # Special: "search <x> on youtube".
            if normalized.startswith("search ") and normalized.endswith(" on youtube"):
                mid = normalized[len("search ") : -len(" on youtube")].strip()
                if mid in _REF_WORDS:
                    mid = _ctx_str(ctx, "last_search_query")
                if not mid:
                    return _clarify(raw_text, "I'm not sure what to search. Please say the search query.")
                return ParsedIntent(
                    intent_type=IntentType.BROWSER,
                    raw_text=raw_text,
                    entities={"engine": "youtube", "query": mid},
                )

            idx = tokens.index("search") if "search" in tokens else 0
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

            if query in _REF_WORDS:
                query = _ctx_str(ctx, "last_search_query")

            if not query:
                return _clarify(raw_text, "I'm not sure what to search. Please say the search query.")

            # Follow-up: if user recently opened YouTube, default searches to YouTube.
            if engine == "google":
                last_site = _ctx_str(ctx, "last_browser_site")
                last_eng = _ctx_str(ctx, "last_search_engine")
                if last_site == "youtube" or last_eng == "youtube":
                    engine = "youtube"

            return ParsedIntent(
                intent_type=IntentType.BROWSER,
                raw_text=raw_text,
                entities={"engine": engine, "query": query},
            )

        return ParsedIntent(intent_type=IntentType.UNKNOWN, raw_text=raw_text)

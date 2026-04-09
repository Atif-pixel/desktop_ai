"""Browser actions.

Safe behavior:
- Open a URL in the default browser

Supports:
- open youtube / open gmail
- search <query> (Google)
- search google <query>
- search youtube <query>

No browser automation beyond opening a URL.
"""

from __future__ import annotations

import webbrowser
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from app.core.types import CommandResult, ParsedIntent


_SITE_URLS = {
    "youtube": "https://www.youtube.com/",
    "gmail": "https://mail.google.com/",
}


def _google_search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _youtube_search_url(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


class BrowserActions:
    """Actions that target the default browser."""

    def handle(self, intent: ParsedIntent) -> CommandResult:
        entities = intent.entities or {}

        site = entities.get("site")
        if isinstance(site, str) and site.strip():
            key = site.strip().lower()
            url = _SITE_URLS.get(key)
            if not url:
                return CommandResult(
                    ok=False,
                    executed=False,
                    message=f"Browser site '{key}' is not supported yet.",
                    data={"site": key},
                )

            return self._open_url(url, message=f"Opening {key}...", extra_data={"site": key})

        query = entities.get("query")
        engine = entities.get("engine")

        if isinstance(query, str) and query.strip():
            q = query.strip()
            eng = engine if isinstance(engine, str) else "google"
            eng = (eng or "google").strip().lower()

            if eng in {"youtube", "yt"}:
                url = _youtube_search_url(q)
                return self._open_url(
                    url,
                    message=f"Searching YouTube: {q}",
                    extra_data={"engine": "youtube", "query": q},
                )

            url = _google_search_url(q)
            return self._open_url(
                url,
                message=f"Searching: {q}",
                extra_data={"engine": "google", "query": q},
            )

        return CommandResult(
            ok=False,
            executed=False,
            message=(
                "Browser command not supported yet. Try 'search <query>', 'search youtube <query>', "
                "'open youtube', 'open gmail', or 'help'."
            ),
            data={"intent": intent.raw_text},
        )

    def _open_url(self, url: str, *, message: str, extra_data: Optional[Dict[str, Any]] = None) -> CommandResult:
        data: Dict[str, Any] = {"url": url}
        if extra_data:
            data.update(extra_data)

        try:
            opened = webbrowser.open(url, new=2)
        except Exception as exc:
            return CommandResult(
                ok=False,
                executed=False,
                message=f"Failed to open browser: {exc}",
                data=data,
            )

        return CommandResult(
            ok=True,
            executed=bool(opened),
            message=message,
            data=data,
        )

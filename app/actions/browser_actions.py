"""Browser actions.

Step 2D safe starter behavior:
- open a search query in the default browser

No browser automation beyond opening a URL.
"""

from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

from app.core.types import CommandResult, ParsedIntent


class BrowserActions:
    """Actions that target the default browser."""

    def handle(self, intent: ParsedIntent) -> CommandResult:
        query = (intent.entities or {}).get("query")
        if isinstance(query, str) and query.strip():
            url = f"https://www.google.com/search?q={quote_plus(query.strip())}"
            try:
                opened = webbrowser.open(url, new=2)
            except Exception as exc:
                return CommandResult(
                    ok=False,
                    executed=False,
                    message=f"Failed to open browser: {exc}",
                    data={"url": url},
                )

            return CommandResult(
                ok=True,
                executed=bool(opened),
                message=f"Searching: {query.strip()}",
                data={"url": url},
            )

        return CommandResult(
            ok=False,
            executed=False,
            message="Browser command not supported yet. Try 'search <query>' or 'help'.",
            data={"intent": intent.raw_text},
        )

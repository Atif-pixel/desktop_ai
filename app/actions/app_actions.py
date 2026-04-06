"""Application actions.

Step 2D safe starter behavior:
- open Notepad
- open Calculator
- open Chrome (best-effort) or fall back to default browser

No app automation beyond launching.
"""

from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import webbrowser
from typing import Optional

from app.core.types import CommandResult, ParsedIntent


_SUPPORTED_APPS = ["notepad", "calculator", "chrome"]


def _find_chrome_exe() -> Optional[str]:
    """Best-effort Chrome path discovery for Windows."""

    candidates = []

    which = shutil.which("chrome")
    if which:
        candidates.append(which)

    program_files = os.environ.get("PROGRAMFILES")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)")
    local_app_data = os.environ.get("LOCALAPPDATA")

    for base in (program_files, program_files_x86, local_app_data):
        if not base:
            continue
        candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))

    for path in candidates:
        if path and os.path.isfile(path):
            return path

    return None


class AppActions:
    """Actions that target applications."""

    def handle(self, intent: ParsedIntent) -> CommandResult:
        command = (intent.entities or {}).get("command")
        if not isinstance(command, str) or not command.strip():
            return CommandResult(
                ok=False,
                executed=False,
                message="No app specified. Try 'open notepad', 'open calculator', or 'open chrome'.",
                data={"intent": intent.raw_text},
            )

        app = command.strip().lower()

        if app in {"notepad", "notepad.exe"}:
            try:
                subprocess.Popen(["notepad.exe"])
            except Exception as exc:
                return CommandResult(ok=False, executed=False, message=f"Failed to open Notepad: {exc}")
            return CommandResult(ok=True, executed=True, message="Opened Notepad.")

        if app in {"calc", "calculator", "calculator.exe"}:
            try:
                subprocess.Popen(["calc.exe"])
            except Exception as exc:
                return CommandResult(ok=False, executed=False, message=f"Failed to open Calculator: {exc}")
            return CommandResult(ok=True, executed=True, message="Opened Calculator.")

        if app in {"chrome", "google chrome"}:
            chrome = _find_chrome_exe()
            if chrome:
                try:
                    subprocess.Popen([chrome])
                except Exception as exc:
                    return CommandResult(ok=False, executed=False, message=f"Failed to open Chrome: {exc}")
                return CommandResult(ok=True, executed=True, message="Opened Chrome.")

            # Fallback: open default browser rather than failing.
            try:
                webbrowser.open("https://www.google.com", new=2)
            except Exception as exc:
                return CommandResult(
                    ok=False,
                    executed=False,
                    message=f"Chrome not found and failed to open default browser: {exc}",
                )

            return CommandResult(
                ok=True,
                executed=True,
                message="Chrome not found; opened default browser instead.",
            )

        closest = difflib.get_close_matches(app, _SUPPORTED_APPS, n=1, cutoff=0.6)
        suggestion = f" Did you mean '{closest[0]}'?" if closest else ""

        return CommandResult(
            ok=False,
            executed=False,
            message=f"App '{app}' is not supported yet." + suggestion + " Supported: notepad, calculator, chrome.",
            data={
                "app": app,
                "supported": _SUPPORTED_APPS,
                "suggestion": closest[0] if closest else None,
            },
        )

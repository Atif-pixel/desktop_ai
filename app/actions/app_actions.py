"""Application actions.

Safe behavior:
- Launching a small set of Windows apps / shell targets
- No destructive actions
- No UI automation

Supported app targets (Step 5B expands coverage):
- notepad
- calculator
- chrome (best-effort; fallback to default browser)
- vscode
- explorer (File Explorer)
- settings (Windows Settings)

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


_SUPPORTED_APPS = ["notepad", "calculator", "chrome", "vscode", "explorer", "settings"]


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


def _find_vscode_exe() -> Optional[str]:
    """Best-effort VS Code discovery for Windows."""

    # If `code` is available on PATH, prefer that.
    which = shutil.which("code")
    if which:
        return which

    candidates = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    program_files = os.environ.get("PROGRAMFILES")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)")

    for base in (local_app_data, program_files, program_files_x86):
        if not base:
            continue
        candidates.append(os.path.join(base, "Programs", "Microsoft VS Code", "Code.exe"))
        candidates.append(os.path.join(base, "Microsoft VS Code", "Code.exe"))

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
                message=(
                    "No app specified. Try 'open notepad', 'open calculator', 'open chrome', "
                    "'open vscode', 'open explorer', or 'open settings'."
                ),
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

        if app in {"vscode", "vs code", "visual studio code", "code"}:
            exe = _find_vscode_exe()
            if not exe:
                return CommandResult(
                    ok=False,
                    executed=False,
                    message=(
                        "VS Code not found. Install Visual Studio Code or ensure the `code` command is on PATH."
                    ),
                    data={"app": "vscode"},
                )

            try:
                subprocess.Popen([exe])
            except Exception as exc:
                return CommandResult(ok=False, executed=False, message=f"Failed to open VS Code: {exc}")

            return CommandResult(ok=True, executed=True, message="Opened VS Code.")

        if app in {"explorer", "file explorer", "windows explorer"}:
            try:
                subprocess.Popen(["explorer.exe"])
            except Exception as exc:
                return CommandResult(ok=False, executed=False, message=f"Failed to open File Explorer: {exc}")

            return CommandResult(ok=True, executed=True, message="Opened File Explorer.")

        if app in {"settings", "windows settings"}:
            # Use the ms-settings URI scheme.
            try:
                subprocess.Popen(["cmd", "/c", "start", "", "ms-settings:"])
            except Exception as exc:
                return CommandResult(ok=False, executed=False, message=f"Failed to open Settings: {exc}")

            return CommandResult(ok=True, executed=True, message="Opened Settings.")

        closest = difflib.get_close_matches(app, _SUPPORTED_APPS, n=1, cutoff=0.6)
        suggestion = f" Did you mean '{closest[0]}'?" if closest else ""

        return CommandResult(
            ok=False,
            executed=False,
            message=f"App '{app}' is not supported yet." + suggestion + " Supported: " + ", ".join(_SUPPORTED_APPS) + ".",
            data={
                "app": app,
                "supported": _SUPPORTED_APPS,
                "suggestion": closest[0] if closest else None,
            },
        )

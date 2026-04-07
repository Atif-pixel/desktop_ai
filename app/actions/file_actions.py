"""File actions.

Step 2D intentionally kept file operations placeholder-safe.
Step 5B adds a small, safe navigation/opening set:
- open Downloads
- open Desktop

No destructive or filesystem-modifying behavior is implemented.
"""

from __future__ import annotations

import os
import subprocess
import sys

from app.core.types import CommandResult, ParsedIntent


def _user_home() -> str:
    return os.path.expanduser("~")


def _known_folder_path(target: str) -> str:
    home = _user_home()
    if target == "downloads":
        return os.path.join(home, "Downloads")
    if target == "desktop":
        return os.path.join(home, "Desktop")
    return home


class FileActions:
    """Actions that target safe filesystem navigation."""

    def handle(self, intent: ParsedIntent) -> CommandResult:
        entities = intent.entities or {}

        target = entities.get("target")
        if isinstance(target, str) and target.strip():
            t = target.strip().lower()
            return self._open_known_target(t)

        command = entities.get("command")
        if isinstance(command, str) and command.strip():
            c = command.strip().lower()

            if c in {"downloads", "open downloads", "open download"}:
                return self._open_known_target("downloads")

            if c in {"desktop", "open desktop"}:
                return self._open_known_target("desktop")

            return CommandResult(
                ok=False,
                executed=False,
                message="File commands are limited. Try 'open downloads', 'open desktop', or 'help'.",
                data={"command": command.strip()},
            )

        return CommandResult(
            ok=False,
            executed=False,
            message="File commands are limited. Try 'open downloads', 'open desktop', or 'help'.",
            data={"intent": intent.raw_text},
        )

    def _open_known_target(self, target: str) -> CommandResult:
        if target not in {"downloads", "desktop"}:
            return CommandResult(
                ok=False,
                executed=False,
                message=f"File target '{target}' is not supported yet.",
                data={"target": target},
            )

        path = _known_folder_path(target)
        if not os.path.isdir(path):
            return CommandResult(
                ok=False,
                executed=False,
                message=f"Folder not found: {path}",
                data={"target": target, "path": path},
            )

        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer.exe", path])
            else:
                os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:
            return CommandResult(
                ok=False,
                executed=False,
                message=f"Failed to open {target}: {exc}",
                data={"target": target, "path": path},
            )

        return CommandResult(
            ok=True,
            executed=True,
            message=f"Opened {target}.",
            data={"target": target, "path": path},
        )

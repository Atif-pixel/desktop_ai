"""File actions (placeholder).

Step 2D intentionally keeps file operations placeholder-safe.
No destructive or filesystem-modifying behavior is implemented yet.
"""

from __future__ import annotations

from app.core.types import CommandResult, ParsedIntent


class FileActions:
    """Actions that target local filesystem operations."""

    def handle(self, intent: ParsedIntent) -> CommandResult:
        command = (intent.entities or {}).get("command")
        if isinstance(command, str) and command.strip():
            return CommandResult(
                ok=False,
                executed=False,
                message="File commands are not implemented yet (placeholder).",
                data={"command": command.strip()},
            )

        return CommandResult(
            ok=False,
            executed=False,
            message="File commands are not implemented yet (placeholder).",
            data={"intent": intent.raw_text},
        )

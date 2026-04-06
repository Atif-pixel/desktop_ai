"""System-level actions.

Step 2D: includes a small, safe starter set.
- `time` returns local time

No risky actions (shutdown/restart/delete) in this step.
"""

from __future__ import annotations

from datetime import datetime

from app.core.enums import IntentType
from app.core.types import CommandResult, ParsedIntent


class SystemActions:
    """System actions such as informational utilities."""

    def handle(self, intent: ParsedIntent) -> CommandResult:
        if intent.intent_type == IntentType.TIME:
            now = datetime.now().astimezone()
            tz = now.tzname() or "local"
            text = now.strftime("%Y-%m-%d %H:%M:%S")
            offset = now.strftime("%z")
            return CommandResult(
                ok=True,
                executed=False,
                message=f"Current time: {text} ({tz} {offset})",
                data={"time": now.isoformat()},
            )

        command = (intent.entities or {}).get("command")
        if isinstance(command, str) and command.strip().lower() == "time":
            now = datetime.now().astimezone()
            return CommandResult(
                ok=True,
                executed=False,
                message=f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}",
                data={"time": now.isoformat()},
            )

        return CommandResult(
            ok=False,
            executed=False,
            message="System command not supported yet. Try 'time' or 'help'.",
            data={"intent": intent.raw_text},
        )

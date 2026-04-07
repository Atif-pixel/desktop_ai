"""System-level actions.

Safe behavior:
- informational utilities (time, date, day)
- conservative volume control (volume up/down/mute)

No risky actions (shutdown/restart/delete) in this step.
"""

from __future__ import annotations

import sys
from datetime import datetime

from app.core.enums import IntentType
from app.core.types import CommandResult, ParsedIntent


def _send_vk(vk: int) -> None:
    """Send a single virtual-key press (down+up) on Windows."""

    import ctypes

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


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
        cmd = command.strip().lower() if isinstance(command, str) else ""

        if cmd == "time":
            now = datetime.now().astimezone()
            return CommandResult(
                ok=True,
                executed=False,
                message=f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}",
                data={"time": now.isoformat()},
            )

        if cmd == "date":
            now = datetime.now().astimezone()
            return CommandResult(
                ok=True,
                executed=False,
                message=f"Today's date: {now.strftime('%Y-%m-%d')}",
                data={"date": now.date().isoformat()},
            )

        if cmd == "day":
            now = datetime.now().astimezone()
            return CommandResult(
                ok=True,
                executed=False,
                message=f"Today is: {now.strftime('%A')}",
                data={"day": now.strftime('%A')},
            )

        if cmd in {"volume_up", "volume_down", "mute", "unmute"}:
            if not sys.platform.startswith("win"):
                return CommandResult(
                    ok=False,
                    executed=False,
                    message="Volume control is only supported on Windows.",
                    data={"command": cmd},
                )

            VK_VOLUME_MUTE = 0xAD
            VK_VOLUME_DOWN = 0xAE
            VK_VOLUME_UP = 0xAF

            try:
                if cmd == "volume_up":
                    _send_vk(VK_VOLUME_UP)
                    return CommandResult(ok=True, executed=True, message="Volume up.")
                if cmd == "volume_down":
                    _send_vk(VK_VOLUME_DOWN)
                    return CommandResult(ok=True, executed=True, message="Volume down.")

                # Mute/unmute are toggle at the OS level.
                _send_vk(VK_VOLUME_MUTE)
                if cmd == "unmute":
                    return CommandResult(ok=True, executed=True, message="Unmute (toggle).")
                return CommandResult(ok=True, executed=True, message="Mute (toggle).")
            except Exception as exc:
                return CommandResult(
                    ok=False,
                    executed=False,
                    message=f"Failed to control volume: {exc}",
                    data={"command": cmd},
                )

        return CommandResult(
            ok=False,
            executed=False,
            message="System command not supported yet. Try 'time', 'date', 'what day is it', or 'help'.",
            data={"intent": intent.raw_text},
        )

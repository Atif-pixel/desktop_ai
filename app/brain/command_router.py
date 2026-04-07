"""Command routing.

Routes a parsed intent to an action handler.

Keeps routing modular:
- intent parsing classifies + extracts parameters
- router picks the action area
- action modules do the real work (or safe placeholders)
"""

from __future__ import annotations

from typing import Optional

from app.actions.app_actions import AppActions
from app.actions.browser_actions import BrowserActions
from app.actions.file_actions import FileActions
from app.actions.system_actions import SystemActions
from app.core.enums import IntentType
from app.core.types import CommandResult, ParsedIntent


_GLOBAL_HELP_TEXT = (
    "Commands:\n"
    "  help                     Show this help\n"
    "  hello | hi               Greeting\n"
    "  time                     Show current time\n"
    "  date                     Show today's date\n"
    "  what day is it           Show day of week\n"
    "  volume up                Increase volume\n"
    "  volume down              Decrease volume\n"
    "  mute                     Toggle mute\n"
    "  open notepad             Launch Notepad\n"
    "  open calculator          Launch Calculator\n"
    "  open chrome              Launch Chrome (or default browser)\n"
    "  open vscode              Launch VS Code\n"
    "  open explorer            Launch File Explorer\n"
    "  open settings            Open Windows Settings\n"
    "  open downloads           Open Downloads folder\n"
    "  open desktop             Open Desktop folder\n"
    "  open youtube             Open YouTube\n"
    "  open gmail               Open Gmail\n"
    "  search <query>           Google search\n"
    "  search google <query>    Google search\n"
    "  search youtube <query>   YouTube search\n"
    "  file <command>           Limited file navigation\n"
    "  voice | listen           (local) One-shot microphone input\n"
    "  text                     (local) Already in text mode\n"
    "  exit | quit | stop        Exit the program"
)


_SECTION_HELP: dict[str, str] = {
    "app": (
        "App commands:\n"
        "  open notepad\n"
        "  open calculator\n"
        "  open chrome\n"
        "  open vscode\n"
        "  open explorer\n"
        "  open settings"
    ),
    "browser": (
        "Browser commands:\n"
        "  open youtube\n"
        "  open gmail\n"
        "  search <query>\n"
        "  search google <query>\n"
        "  search youtube <query>"
    ),
    "system": (
        "System commands:\n"
        "  time\n"
        "  date\n"
        "  what day is it\n"
        "  volume up\n"
        "  volume down\n"
        "  mute"
    ),
    "file": (
        "File commands:\n"
        "  open downloads\n"
        "  open desktop\n"
        "  file downloads\n"
        "  file desktop"
    ),
}


class CommandRouter:
    """Route intents to action handlers."""

    def __init__(
        self,
        system_actions: Optional[SystemActions] = None,
        app_actions: Optional[AppActions] = None,
        browser_actions: Optional[BrowserActions] = None,
        file_actions: Optional[FileActions] = None,
    ) -> None:
        self._system = system_actions or SystemActions()
        self._app = app_actions or AppActions()
        self._browser = browser_actions or BrowserActions()
        self._files = file_actions or FileActions()

    def route(self, intent: ParsedIntent) -> CommandResult:
        entities = intent.entities or {}
        builtin = entities.get("builtin")

        if builtin == "help":
            section = entities.get("section")
            if isinstance(section, str) and section.strip():
                key = section.strip().lower()
                text = _SECTION_HELP.get(key)
                if text:
                    return CommandResult(
                        ok=True,
                        executed=False,
                        message=text,
                        data={"builtin": "help", "section": key},
                    )

            return CommandResult(
                ok=True,
                executed=False,
                message=_GLOBAL_HELP_TEXT,
                data={"builtin": "help"},
            )

        if builtin == "greet":
            return CommandResult(
                ok=True,
                executed=False,
                message="Hi. Type 'help' to see available commands.",
                data={"builtin": "greet"},
            )

        if intent.intent_type == IntentType.EXIT:
            return CommandResult(
                ok=True,
                executed=False,
                message="Exiting.",
                data={"builtin": "exit"},
            )

        if intent.intent_type in {IntentType.TIME, IntentType.SYSTEM}:
            return self._system.handle(intent)

        if intent.intent_type == IntentType.APP:
            return self._app.handle(intent)

        if intent.intent_type == IntentType.BROWSER:
            return self._browser.handle(intent)

        if intent.intent_type == IntentType.FILE:
            return self._files.handle(intent)

        return CommandResult(
            ok=False,
            executed=False,
            message="Unknown command. Type 'help' for options.",
            data={"intent": intent.raw_text, "intent_type": intent.intent_type.value},
        )

"""Command routing.

Routes a parsed intent to an action handler.

Step 2D keeps routing modular:
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
            return CommandResult(
                ok=True,
                executed=False,
                message=(
                    "Commands:\n"
                    "  help                     Show this help\n"
                    "  hello | hi               Greeting\n"
                    "  time                     Show current time\n"
                    "  open notepad             Launch Notepad\n"
                    "  open calculator          Launch Calculator\n"
                    "  open chrome              Launch Chrome (or default browser)\n"
                    "  search <query>           Open browser search\n"
                    "  file <command>           File placeholder\n"
                    "  voice | listen           (local) One-shot microphone input\n"
                    "  text                     (local) Already in text mode\n"
                    "  exit | quit | stop        Exit the program"
                ),
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



"""Canonical app entrypoint.

Step 2C provides a simple terminal text-input loop to exercise the voice-first
assistant pipeline end-to-end before real microphone/STT/TTS integration.

Important:
- No gesture runtime
- No microphone capture
- No speech-to-text capture
- No TTS

Run:
  python -m app.main
"""

from __future__ import annotations

from typing import Iterable, Optional

from app.services.assistant_runtime import AssistantRuntime


_EXIT_COMMANDS = {"exit", "quit", "stop"}


def _is_exit_command(text: str) -> bool:
    return text.strip().lower() in _EXIT_COMMANDS


def run_text_loop(runtime: AssistantRuntime, *, prompt: str = "> ") -> int:
    """Run a blocking terminal loop.

    This is intentionally the simplest possible flow that can later be swapped
    out for microphone + speech-to-text without changing the assistant core.
    """

    print("Desktop Control AI (text mode)")
    print("Type 'help' for commands. Type 'exit' to quit.")

    while True:
        try:
            user_text = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()  # newline
            break

        if not user_text.strip():
            continue

        if _is_exit_command(user_text):
            break

        response = runtime.process_text(user_text)
        print(response.text)

    print("Goodbye.")
    return 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Program entrypoint.

    `argv` is reserved for future CLI args (not used in Step 2C).
    """

    _ = argv
    runtime = AssistantRuntime()
    return run_text_loop(runtime)


if __name__ == "__main__":
    raise SystemExit(main())

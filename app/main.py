"""Canonical app entrypoint.

Text-mode remains the primary dev harness.

Step 3A added an optional, controlled one-shot voice input trigger.
Step 3B improves voice-mode usability/diagnostics while keeping the same pipeline.
Step 4 adds optional text-to-speech (TTS) output.
Step 5A adds an optional hotkey trigger for one-shot voice input.

Important:
- No gesture runtime
- No wakeword
- No continuous / always-listening mode

Run:
  python -m app.main
"""

from __future__ import annotations

import threading
from typing import Iterable, Optional

from app.input.voice.hotkey import HotkeyListener
from app.services.assistant_runtime import AssistantRuntime


_EXIT_COMMANDS = {"exit", "quit", "stop"}
_TEXT_COMMANDS = {"text"}
_VOICE_COMMANDS = {"voice", "listen"}


def _normalized(text: str) -> str:
    return text.strip().lower()


def _is_exit_command(text: str) -> bool:
    return _normalized(text) in _EXIT_COMMANDS


def _is_text_command(text: str) -> bool:
    return _normalized(text) in _TEXT_COMMANDS


def _is_voice_command(text: str) -> bool:
    return _normalized(text) in _VOICE_COMMANDS


def _format_voice_diagnostics(d: dict) -> str:
    device_name = d.get("device_name")
    device_index = d.get("device_index")
    sr = d.get("sample_rate_hz")
    dur = d.get("duration_seconds")
    peak = d.get("peak")
    rms = d.get("rms")

    device_part = None
    if device_name and device_index is not None:
        device_part = f"{device_name} (index {device_index})"
    elif device_index is not None:
        device_part = f"index {device_index}"
    elif device_name:
        device_part = str(device_name)

    parts = []
    if device_part:
        parts.append(f"Mic: {device_part}")
    if sr:
        parts.append(f"sr={sr}Hz")
    if dur:
        parts.append(f"dur={dur:.2f}s")
    if peak is not None:
        parts.append(f"peak={peak}")
    if rms is not None:
        parts.append(f"rms={rms:.1f}")

    return " | ".join(parts)


def _print_and_speak(runtime: AssistantRuntime, response) -> None:
    print(response.text)
    runtime.speak_response(response)


def _run_one_shot_voice(runtime: AssistantRuntime, *, source: str, lock: threading.Lock) -> None:
    # Avoid overlapping voice capture if both typed command + hotkey are used.
    if not lock.acquire(blocking=False):
        print("Already listening...")
        return

    try:
        max_s = runtime.settings.voice_max_seconds
        print(f"\nListening... (one-shot, up to {max_s:.0f}s) [{source}]")

        listen = runtime.listen_once()
        diag_line = _format_voice_diagnostics(listen.diagnostics)
        if diag_line:
            print(diag_line)

        if not listen.ok or not listen.transcript:
            print(listen.error or "Voice input failed.")
            return

        # Requirement: print transcript before processing it.
        print(f"Heard: {listen.transcript.text}")

        response = runtime.process_text(listen.transcript.text)
        _print_and_speak(runtime, response)
    finally:
        lock.release()


def run_text_loop(runtime: AssistantRuntime, *, prompt: str = "> ") -> int:
    """Run a blocking terminal loop."""

    print("Desktop Control AI (text mode)")
    print("Type 'help' for commands.")
    print("Type 'voice' to speak once. Type 'text' to confirm text mode. Type 'exit' to quit.")

    voice_lock = threading.Lock()

    hotkey_listener = None
    if getattr(runtime.settings, "hotkey_enabled", False):
        combo = getattr(runtime.settings, "hotkey_combo", "shift+v")

        def on_hotkey() -> None:
            # Keep callback light; do work in a separate thread.
            threading.Thread(
                target=_run_one_shot_voice,
                kwargs={"runtime": runtime, "source": f"hotkey:{combo}", "lock": voice_lock},
                daemon=True,
            ).start()

        hotkey_listener = HotkeyListener(combo, on_hotkey)
        status = hotkey_listener.start()
        if status.ok:
            print(f"Hotkey: press {combo} to speak once.")
        else:
            print(f"Hotkey unavailable ({combo}): {status.error}")
            hotkey_listener = None

    try:
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

            if _is_text_command(user_text):
                print("Already in text mode.")
                continue

            if _is_voice_command(user_text):
                _run_one_shot_voice(runtime, source="typed", lock=voice_lock)
                continue

            response = runtime.process_text(user_text)
            _print_and_speak(runtime, response)

    finally:
        if hotkey_listener is not None:
            hotkey_listener.stop()

    print("Goodbye.")
    return 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Program entrypoint."""

    _ = argv
    runtime = AssistantRuntime()
    return run_text_loop(runtime)


if __name__ == "__main__":
    raise SystemExit(main())




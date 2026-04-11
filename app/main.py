"""Canonical app entrypoint.

Text-mode remains the primary dev harness.

Optional modes:
- `--tray`: run as a system tray app (no interactive CLI)
- `--background`: start tray mode in the background (Windows best-effort)

Important:
- No gesture runtime
- No wakeword
- No continuous / always-listening mode

Run:
  python -m app.main
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
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


def _status(tag: str, message: str) -> None:
    print(f"[{tag}] {message}")


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


def _is_help_response(response) -> bool:
    result = getattr(response, "result", None)
    data = getattr(result, "data", None) if result is not None else None
    return isinstance(data, dict) and data.get("builtin") == "help"


def _is_section_help_response(response) -> bool:
    result = getattr(response, "result", None)
    data = getattr(result, "data", None) if result is not None else None
    return _is_help_response(response) and isinstance(data, dict) and bool(data.get("section"))


def _is_clarify_response(response) -> bool:
    result = getattr(response, "result", None)
    data = getattr(result, "data", None) if result is not None else None
    return isinstance(data, dict) and data.get("builtin") == "clarify"


def _print_response(response) -> None:
    text = (getattr(response, "text", "") or "").rstrip()

    # Preserve help formatting (multi-line blocks) exactly.
    if _is_help_response(response) or "\n" in text:
        print(text)
        return

    if _is_clarify_response(response):
        _status("clarify", text)
        return

    _status("assistant", text)


def _print_and_speak(runtime: AssistantRuntime, response, *, show_speaking_status: bool) -> None:
    _print_response(response)

    if runtime.settings.tts_enabled and show_speaking_status:
        _status("tts", "Speaking...")

    runtime.speak_response(response)


def _run_one_shot_voice(
    runtime: AssistantRuntime,
    *,
    source: str,
    lock: threading.Lock,
) -> None:
    # Avoid overlapping voice capture if both typed command + hotkey are used.
    if not lock.acquire(blocking=False):
        _status("voice", "Already listening...")
        return

    try:
        max_s = runtime.settings.voice_max_seconds
        _status("voice", f"Listening (one-shot, up to {max_s:.0f}s) [{source}]")

        listen = runtime.listen_once()

        diag_line = _format_voice_diagnostics(listen.diagnostics)
        if diag_line and (runtime.settings.voice_show_diagnostics or not listen.ok):
            _status("diag", diag_line)

        if not listen.ok or not listen.transcript:
            _status("error", listen.error or "Voice input failed.")
            return

        # Requirement: show transcript before processing it.
        _status("heard", listen.transcript.text)

        _status("assistant", "Processing...")
        response = runtime.process_text(listen.transcript.text)
        _print_and_speak(runtime, response, show_speaking_status=True)

        _status("idle", "Ready.")
    finally:
        lock.release()


def run_text_loop(runtime: AssistantRuntime, *, prompt: str = "> ") -> int:
    """Run a blocking terminal loop."""

    print("Desktop Control AI")
    _status("idle", "Ready. Type 'help' for commands. Type 'voice' to speak once. Type 'exit' to quit.")

    voice_lock = threading.Lock()

    hotkey_listener = None
    if getattr(runtime.settings, "hotkey_enabled", False):
        combo = getattr(runtime.settings, "hotkey_combo", "shift+v")

        def on_hotkey() -> None:
            threading.Thread(
                target=_run_one_shot_voice,
                kwargs={"runtime": runtime, "source": f"hotkey:{combo}", "lock": voice_lock},
                daemon=True,
            ).start()

        hotkey_listener = HotkeyListener(combo, on_hotkey)
        status = hotkey_listener.start()
        if status.ok:
            _status("hotkey", f"Press {combo} to speak once.")
        else:
            _status("hotkey", f"Unavailable ({combo}): {status.error}")
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
                _status("idle", "Already in text mode.")
                continue

            if _is_voice_command(user_text):
                _run_one_shot_voice(runtime, source="typed", lock=voice_lock)
                continue

            response = runtime.process_text(user_text)
            _print_and_speak(runtime, response, show_speaking_status=False)

    finally:
        if hotkey_listener is not None:
            hotkey_listener.stop()

    _status("idle", "Goodbye.")
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="desktop-control-ai", add_help=True)
    p.add_argument(
        "--tray",
        action="store_true",
        help="Run as a system tray app (no interactive CLI).",
    )
    p.add_argument(
        "--background",
        action="store_true",
        help="Start tray mode in the background (Windows) and exit this process.",
    )
    return p


def _find_pythonw() -> Optional[str]:
    exe = sys.executable or ""
    exe_dir = os.path.dirname(exe)
    candidate = os.path.join(exe_dir, "pythonw.exe")
    return candidate if os.path.isfile(candidate) else None


def _start_tray_in_background() -> bool:
    """Start tray mode in a detached process (best-effort, Windows-friendly)."""

    try:
        exe = _find_pythonw() or sys.executable
        if not exe:
            return False

        args = [exe, "-m", "app.main", "--tray"]

        creationflags = 0
        if sys.platform.startswith("win"):
            creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)

        subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        return True
    except Exception:
        return False


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Program entrypoint."""

    parser = _build_arg_parser()
    ns = parser.parse_args(list(argv) if argv is not None else None)

    if ns.background:
        ok = _start_tray_in_background()
        if ok:
            _status("tray", "Started in background.")
            return 0

        _status("tray", "Failed to start in background. Try `python -m app.main --tray`.")
        return 1

    runtime = AssistantRuntime()

    if ns.tray:
        from app.services.tray_app import TrayApp

        return TrayApp(runtime).run()

    return run_text_loop(runtime)


if __name__ == "__main__":
    raise SystemExit(main())

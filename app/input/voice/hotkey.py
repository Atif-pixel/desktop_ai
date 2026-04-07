"""Hotkey / push-to-talk trigger (Step 5A).

Goal:
- Provide a practical hotkey that triggers the existing one-shot voice pipeline
- Do not add wakeword or continuous listening

This module is intentionally small and optional. If the `keyboard` dependency is
unavailable or fails to hook, the app should still work via typed commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


class HotkeyError(RuntimeError):
    """Hotkey registration or runtime failure."""


@dataclass(frozen=True)
class HotkeyStatus:
    """Result of attempting to register a hotkey."""

    ok: bool
    hotkey: str
    error: Optional[str] = None


class HotkeyListener:
    """Register a hotkey and call a callback on press."""

    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self._hotkey = hotkey
        self._callback = callback
        self._keyboard = None
        self._handle = None

    @property
    def hotkey(self) -> str:
        return self._hotkey

    def start(self) -> HotkeyStatus:
        """Try to register the hotkey.

        Returns a status object; never raises for missing optional deps.
        """

        try:
            import keyboard  # type: ignore

            self._keyboard = keyboard
        except Exception as exc:
            return HotkeyStatus(ok=False, hotkey=self._hotkey, error=f"keyboard import failed: {exc}")

        try:
            # `add_hotkey` is non-blocking and runs the callback in a background thread.
            self._handle = self._keyboard.add_hotkey(self._hotkey, self._callback)
            return HotkeyStatus(ok=True, hotkey=self._hotkey)
        except Exception as exc:
            return HotkeyStatus(ok=False, hotkey=self._hotkey, error=str(exc))

    def stop(self) -> None:
        """Unregister the hotkey if registered."""

        try:
            if self._keyboard is not None and self._handle is not None:
                self._keyboard.remove_hotkey(self._handle)
        except Exception:
            # Never crash on shutdown.
            pass
        finally:
            self._handle = None

    def __enter__(self) -> "HotkeyListener":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

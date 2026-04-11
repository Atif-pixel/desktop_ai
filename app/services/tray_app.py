"""System tray integration (Step 9/10).

Tray mode:
- no interactive CLI loop
- minimal menu: Listen once / Exit
- reuses the existing one-shot voice pipeline and TTS
- preserves hotkey support (if enabled)

Step 10 adds an optional lightweight wake word trigger for tray mode.
"""

from __future__ import annotations

import threading
from typing import Optional

from app.input.voice.hotkey import HotkeyListener
from app.input.voice.wakeword import WakeWordListener
from app.services.assistant_runtime import AssistantRuntime


class TrayApp:
    """Small wrapper around a system tray icon."""

    def __init__(self, runtime: AssistantRuntime) -> None:
        self._runtime = runtime
        self._lock = threading.Lock()
        self._hotkey: Optional[HotkeyListener] = None
        self._wake: Optional[WakeWordListener] = None

    def run(self) -> int:
        """Run the tray icon loop (blocking)."""

        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception as exc:
            print(f"Tray mode unavailable: {exc}")
            return 1

        image = self._build_image(Image, ImageDraw)

        def on_listen(icon, item) -> None:  # noqa: ARG001
            self._start_listen_thread(icon, source="tray")

        def on_exit(icon, item) -> None:  # noqa: ARG001
            try:
                if self._wake is not None:
                    self._wake.stop()
                if self._hotkey is not None:
                    self._hotkey.stop()
            finally:
                icon.stop()

        menu = pystray.Menu(
            pystray.MenuItem("Listen once", on_listen),
            pystray.MenuItem("Exit", on_exit),
        )

        icon = pystray.Icon("Desktop Control AI", image, "Desktop Control AI", menu)

        # Hotkey trigger.
        if getattr(self._runtime.settings, "hotkey_enabled", False):
            combo = getattr(self._runtime.settings, "hotkey_combo", "shift+v")

            def on_hotkey() -> None:
                self._start_listen_thread(icon, source=f"hotkey:{combo}")

            self._hotkey = HotkeyListener(combo, on_hotkey)
            status = self._hotkey.start()
            if not status.ok:
                self._hotkey = None
                try:
                    icon.notify(f"Hotkey unavailable: {status.error}", title="Desktop Control AI")
                except Exception:
                    pass

        # Wake word trigger (tray mode only, opt-in).
        wake_enabled = bool(getattr(self._runtime.settings, "wake_word_enabled", False))
        phrases = getattr(self._runtime.settings, "wake_word_phrases", ("hey jarvis", "jarvis"))
        print(f"wake_word_enabled={wake_enabled} phrases={phrases}")

        if wake_enabled:
            def on_wake(keyword: str) -> None:
                print(f"Wake word detected: {keyword}")
                self._start_listen_thread(icon, source="wakeword")

            self._wake = WakeWordListener(
                phrases=phrases,
                on_wake=on_wake,
                sample_rate_hz=getattr(self._runtime.settings, "voice_sample_rate_hz", 16000),
                device_index=getattr(self._runtime.settings, "voice_device_index", None),
                channels=getattr(self._runtime.settings, "voice_channels", 1),
            )

            st = self._wake.start()
            if st.ok:
                print("Wake listener started")
            else:
                self._wake = None
                try:
                    icon.notify(f"Wake word unavailable: {st.error}", title="Desktop Control AI")
                except Exception:
                    pass

        icon.run()
        return 0

    def _start_listen_thread(self, icon, *, source: str) -> None:
        threading.Thread(target=self._listen_once, args=(icon, source), daemon=True).start()

    def _listen_once(self, icon, source: str) -> None:
        if not self._lock.acquire(blocking=False):
            try:
                icon.notify("Already listening...", title="Desktop Control AI")
            except Exception:
                pass
            return

        wake = self._wake
        wake_enabled = bool(getattr(self._runtime.settings, "wake_word_enabled", False))

        try:
            # Avoid audio device contention: pause wake listening while recording the command.
            if wake is not None and wake.is_running():
                wake.stop()

            if source == "wakeword":
                # Requirement: greet only for wake-word triggers (not hotkey/tray).
                self._runtime.greet_user()

            try:
                icon.notify(f"Listening... ({source})", title="Desktop Control AI")
            except Exception:
                pass

            listen = self._runtime.listen_once()
            if not listen.ok or not listen.transcript:
                err = listen.error or "Voice input failed."
                try:
                    icon.notify(err, title="Desktop Control AI")
                except Exception:
                    pass
                return

            response = self._runtime.process_text(listen.transcript.text)
            self._runtime.speak_response(response)

            try:
                icon.notify(response.text, title="Desktop Control AI")
            except Exception:
                pass
        except Exception as exc:
            print(f"Tray listen flow error: {exc}")
        finally:
            self._lock.release()

            # Resume wake word listener if configured.
            if wake_enabled and wake is not None and not wake.is_running():
                wake.start()

    @staticmethod
    def _build_image(Image, ImageDraw):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((6, 6, 58, 58), fill=(40, 90, 160, 255))
        draw.text((22, 20), "AI", fill=(255, 255, 255, 255))
        return img

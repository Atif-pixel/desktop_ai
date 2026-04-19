"""System tray integration (Step 9/10).

Tray mode:
- no interactive CLI loop
- minimal menu: Listen once / Exit
- reuses the existing one-shot voice pipeline and TTS
- preserves hotkey support (if enabled)

Wake word (Step 10): optional, tray-only.
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
        self._command_thread: Optional[threading.Thread] = None

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
            print("Tray exit triggered")
            try:
                # Stop runtime first so background loops can exit naturally.
                self._runtime.stop()

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
        phrases = getattr(self._runtime.settings, "wake_word_phrases", ("wake up buddy daddy's home", "jarvis"))
        print(f"wake_word_enabled={wake_enabled} phrases={phrases}")

        if wake_enabled:
            # Requirement: wake listener uses 16000Hz.
            sample_rate_hz = 16000
            cfg_sr = getattr(self._runtime.settings, "voice_sample_rate_hz", 16000)
            if int(cfg_sr) != 16000:
                print(f"Wake listener forcing sample_rate_hz=16000 (settings voice_sample_rate_hz={cfg_sr})")

            def on_wake(keyword: str) -> None:
                # Called from the wake listener thread. Keep it lightweight.
                print(f"Wake word detected: {keyword}")
                self._start_command_mode_thread(icon, keyword=keyword)

            self._wake = WakeWordListener(
                phrases=phrases,
                on_wake=on_wake,
                sample_rate_hz=sample_rate_hz,
                device_index=getattr(self._runtime.settings, "voice_device_index", None),
                channels=getattr(self._runtime.settings, "voice_channels", 1),
            )

            st = self._wake.start()
            if st.ok:
                self._runtime.wake_listener = self._wake
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

    def _start_command_mode_thread(self, icon, *, keyword: str) -> None:
        # One-time wake activation.
        if not getattr(self._runtime, "wake_mode", True):
            return

        if self._command_thread is not None and self._command_thread.is_alive():
            return

        self._command_thread = threading.Thread(
            target=self._enter_command_mode,
            args=(icon, keyword),
            daemon=True,
        )
        self._command_thread.start()

    def _enter_command_mode(self, icon, keyword: str) -> None:
        _ = keyword

        if not getattr(self._runtime, "wake_mode", True):
            return

        # Hold the same lock used by one-shot voice so command mode is exclusive.
        if not self._lock.acquire(blocking=False):
            print("Wake->command mode switch blocked: already listening")
            return

        try:
            self._runtime.wake_mode = False

            # Stop wake listener for command mode, but keep reference to restart later
            wake = self._wake
            if wake is not None:
                wake.stop()
            self._runtime.wake_listener = None

            # Requirement: greet only on wake word.
            self._runtime.greet_user()

            print("Switched to command mode")
            try:
                icon.notify("Command mode active", title="Desktop Control AI")
            except Exception:
                pass

            self._runtime.run_continuous_listener(on_exit_callback=self._on_command_mode_exit)
        except Exception as exc:
            print(f"Command mode crashed: {exc}")
        finally:
            self._lock.release()

    def _on_command_mode_exit(self) -> None:
        print("Command mode exited, restarting wake word listener...")
        self._runtime.wake_mode = True

        # Restart wake listener safely
        if self._wake and not self._wake.is_running():
            print("Restarting wake listener...")
            st = self._wake.start()
            if st.ok:
                self._runtime.wake_listener = self._wake
                print("Wake listener restarted successfully.")
            else:
                print(f"Failed to restart wake listener: {st.error}")

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

            # Resume wake word listener only if still in wake mode.
            if (
                wake_enabled
                and getattr(self._runtime, "wake_mode", True)
                and wake is not None
                and not wake.is_running()
            ):
                wake.start()

    @staticmethod
    def _build_image(Image, ImageDraw):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((6, 6, 58, 58), fill=(40, 90, 160, 255))
        draw.text((22, 20), "AI", fill=(255, 255, 255, 255))
        return img

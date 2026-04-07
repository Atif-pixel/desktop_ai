"""Text-to-speech.

Step 4: basic local/offline-friendly TTS suitable for Windows 10/11.

Design goals:
- Additive: terminal output stays primary; TTS is optional
- Failure-safe: TTS errors must not break the assistant
- Dependency-conscious: prefer a built-in Windows path first
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional


class TextToSpeechError(RuntimeError):
    """Text-to-speech failure."""


class TextToSpeech:
    """Speak text to the user."""

    def speak(self, text: str) -> None:
        raise NotImplementedError


class NullTextToSpeech(TextToSpeech):
    """No-op TTS backend."""

    def speak(self, text: str) -> None:
        _ = text
        return None


@dataclass(frozen=True)
class TextToSpeechConfig:
    """Minimal tuning for TTS output."""

    enabled: bool = True
    rate: int = 0


class WindowsPowerShellTextToSpeech(TextToSpeech):
    """TTS via Windows PowerShell + .NET `System.Speech`.

    Implementation notes:
    - Uses `stdin` to pass response text (avoids brittle quoting/escaping)
    - Returns a clean error if PowerShell fails
    """

    def __init__(self, *, rate: int = 0, executable: Optional[str] = None) -> None:
        self._rate = _clamp_int(rate, -10, 10)
        self._exe = executable or _find_windows_powershell_exe()
        if not self._exe:
            raise TextToSpeechError("PowerShell executable not found.")

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return None

        proc = _run_powershell_system_speech(
            exe_path=self._exe,
            text=text,
            rate=self._rate,
        )

        if proc.returncode == 0:
            return None

        # Retry once with 32-bit PowerShell if available (some systems behave differently).
        alt = _find_windows_powershell_exe(prefer_syswow64=True)
        if alt and os.path.abspath(alt).lower() != os.path.abspath(self._exe).lower():
            proc2 = _run_powershell_system_speech(exe_path=alt, text=text, rate=self._rate)
            if proc2.returncode == 0:
                return None
            proc = proc2

        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        details = stderr or stdout
        if details:
            details = " ".join(details.split())
            raise TextToSpeechError(f"PowerShell TTS failed (rc={proc.returncode}): {details}")

        raise TextToSpeechError(f"PowerShell TTS failed (rc={proc.returncode}).")


def default_text_to_speech(config: TextToSpeechConfig) -> TextToSpeech:
    """Create a default TTS backend for the current platform."""

    if not config.enabled:
        return NullTextToSpeech()

    if sys.platform.startswith("win"):
        try:
            return WindowsPowerShellTextToSpeech(rate=config.rate)
        except Exception:
            return NullTextToSpeech()

    # Non-Windows: keep TTS disabled until a cross-platform backend is added.
    return NullTextToSpeech()


def _run_powershell_system_speech(*, exe_path: str, text: str, rate: int) -> subprocess.CompletedProcess[str]:
    # Read text from stdin to avoid quoting/escaping problems.
    script = (
        "$ErrorActionPreference='Stop';"
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$rate={int(rate)};"
        "try { $s.Rate=$rate } catch { } ;"
        "$t=[Console]::In.ReadToEnd();"
        "if (-not [string]::IsNullOrWhiteSpace($t)) { $s.Speak($t) }"
    )

    try:
        return subprocess.run(
            [
                exe_path,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-STA",
                "-WindowStyle",
                "Hidden",
                "-Command",
                script,
            ],
            input=text,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:  # pragma: no cover
        raise TextToSpeechError(f"Failed to run PowerShell TTS: {exc}") from exc


def _clamp_int(value: int, lo: int, hi: int) -> int:
    try:
        v = int(value)
    except Exception:
        v = 0
    return max(lo, min(hi, v))


def _find_windows_powershell_exe(*, prefer_syswow64: bool = False) -> Optional[str]:
    # Prefer Windows PowerShell 5.1 for System.Speech availability.
    system_root = os.environ.get("SystemRoot")
    if system_root:
        if prefer_syswow64:
            candidate = os.path.join(
                system_root, "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe"
            )
        else:
            candidate = os.path.join(
                system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"
            )
        if os.path.isfile(candidate):
            return candidate

    # Fallback: PATH.
    return shutil.which("powershell.exe") or shutil.which("powershell")

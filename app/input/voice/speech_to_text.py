"""Speech-to-text.

Step 3A added a practical, dependency-conscious STT option for Windows:
- Vosk offline transcription (requires a downloaded Vosk model directory)

Step 3B improves error clarity and debug visibility (confidence when available).

Notes:
- Optional dependencies (e.g., `vosk`) are imported lazily so text-mode runs
  even if voice deps are not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .microphone import AudioChunk


@dataclass(frozen=True)
class Transcript:
    """Speech-to-text output."""

    text: str
    confidence: Optional[float] = None


class SpeechToTextError(RuntimeError):
    """Speech-to-text failure."""


class SpeechNotUnderstood(SpeechToTextError):
    """Audio was captured, but speech could not be recognized."""


class SpeechToText:
    """Transcribe captured audio into text."""

    def transcribe(self, chunk: AudioChunk) -> Transcript:
        raise NotImplementedError


class VoskSpeechToText(SpeechToText):
    """Offline speech-to-text using Vosk.

    Model lookup order (Step 3B):
    1) `model_dir` argument (if provided)
    2) env `DESKTOP_CONTROL_AI_VOSK_MODEL`
    3) env `VOSK_MODEL_PATH`
    4) project_root/model/vosk-model-small-en-us-0.15
    5) first valid Vosk model directory inside project_root/model/

    A directory is considered a Vosk model if it contains `am/final.mdl`.
    """

    def __init__(self, model_dir: Optional[str] = None) -> None:
        self._model_dir = model_dir
        self._model = None

    @staticmethod
    def _project_root() -> Path:
        # app/input/voice/speech_to_text.py -> project root
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def _is_valid_vosk_model_dir(model_dir: Path) -> bool:
        """Best-effort validation that `model_dir` looks like a Vosk model."""

        if not model_dir.is_dir():
            return False

        return (model_dir / "am" / "final.mdl").is_file()

    def _resolve_model_dir(self) -> str:
        import os

        project_root = self._project_root()
        model_root = project_root / "model"

        candidates: list[Path] = []
        searched: list[str] = []

        if self._model_dir:
            candidates.append(Path(self._model_dir).expanduser())
            searched.append(f"model_dir argument: {self._model_dir}")

        env1 = os.environ.get("DESKTOP_CONTROL_AI_VOSK_MODEL")
        env2 = os.environ.get("VOSK_MODEL_PATH")
        if env1:
            candidates.append(Path(env1).expanduser())
            searched.append("env: DESKTOP_CONTROL_AI_VOSK_MODEL")
        if env2:
            candidates.append(Path(env2).expanduser())
            searched.append("env: VOSK_MODEL_PATH")

        preferred = model_root / "vosk-model-small-en-us-0.15"
        candidates.append(preferred)
        searched.append(f"default: {preferred}")

        if model_root.is_dir():
            searched.append(f"scan: first valid under {model_root}")
            try:
                for child in sorted(model_root.iterdir()):
                    if child.is_dir():
                        candidates.append(child)
            except Exception:
                searched.append(f"scan: failed to read {model_root}")
        else:
            searched.append(f"scan: {model_root} does not exist")

        for c in candidates:
            try:
                resolved = c.resolve()
            except Exception:
                resolved = c

            if self._is_valid_vosk_model_dir(resolved):
                return str(resolved)

        looked_in = "\n- ".join(searched) if searched else "(none)"
        raise SpeechToTextError(
            "Vosk model not found. Looked in:\n- "
            + looked_in
            + "\n\nSet VOSK_MODEL_PATH (or DESKTOP_CONTROL_AI_VOSK_MODEL) or place a model under project_root/model/."
        )

    def _get_model(self):
        if self._model is not None:
            return self._model

        model_dir = self._resolve_model_dir()

        try:
            from vosk import Model  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise SpeechToTextError(
                "Voice dependencies are not installed. Install `vosk` to use speech-to-text."
            ) from exc

        self._model = Model(model_dir)
        return self._model

    def transcribe(self, chunk: AudioChunk) -> Transcript:
        import json

        if not chunk.data:
            raise SpeechToTextError("Empty audio.")

        if chunk.sample_rate_hz <= 0:
            raise SpeechToTextError("Invalid sample rate.")

        model = self._get_model()

        try:
            from vosk import KaldiRecognizer  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise SpeechToTextError("Failed to import Vosk recognizer.") from exc

        recognizer = KaldiRecognizer(model, float(chunk.sample_rate_hz))
        recognizer.AcceptWaveform(chunk.data)
        result_raw = recognizer.FinalResult()

        try:
            payload = json.loads(result_raw)
        except Exception as exc:
            raise SpeechToTextError("Failed to parse STT result.") from exc

        text = (payload.get("text") or "").strip()
        if not text:
            raise SpeechNotUnderstood("Speech captured, but could not be understood.")

        confidence = None
        results = payload.get("result")
        if isinstance(results, list) and results:
            confs = [
                r.get("conf")
                for r in results
                if isinstance(r, dict) and isinstance(r.get("conf"), (int, float))
            ]
            if confs:
                confidence = float(sum(confs) / len(confs))

        return Transcript(text=text, confidence=confidence)

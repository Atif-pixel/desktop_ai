# Desktop Control AI (Windows 10/11)

Voice-first desktop assistant foundation for Windows.

## Purpose
Build a production-grade assistant that can control the desktop using voice (primary) and later gestures (secondary).

## Current Direction
- Voice-first architecture under `app/`
- Gesture code exists only as dormant legacy experiments under `gesture/` and `scripts/experiments/gesture/`
- No gesture runtime is active

## Current Status (Step 10)
- The assistant is runnable in **text-mode**.
- A controlled **one-shot voice input** path is available as a bridge before adding:
  - continuous listening
  - advanced wake word models
- Basic **text-to-speech (TTS)** is available and will speak assistant responses while still printing them.
- An optional **system tray** mode is available.
- An optional lightweight **wake word trigger** is available in tray mode.

Text-mode remains the fallback and should keep working even if voice dependencies/models are missing.

## Architecture Overview
Text-mode and voice-mode share the same pipeline:

`input(text)` -> `intent` -> `orchestrator` -> `action` -> `response`

Voice-mode is one-shot:

`mic` -> `speech-to-text` -> `input(text)` -> (same pipeline)

Output:
- responses are printed to the terminal
- and optionally spoken via TTS

Concrete runtime flow:
- `app/main.py` (terminal loop or tray entry)
- `app/services/assistant_runtime.py` (runtime wiring + one-shot voice coordination)
- `app/brain/orchestrator.py` (coordinates brain pipeline)
- `app/brain/intent_parser.py` (deterministic parsing)
- `app/brain/command_router.py` (routes to actions)
- `app/actions/*` (does safe work or returns placeholder results)
- `app/output/responder.py` (builds final response)
- `app/output/text_to_speech.py` (speaks responses; failure-safe)

## Folder Structure
Top-level:
- `app/` voice-first assistant code
- `gesture/` dormant legacy gesture modules (not used by runtime)
- `scripts/experiments/gesture/` dormant gesture experiment scripts (not used by runtime)
- `tests/` placeholder test package

Inside `app/`:
- `app/input/voice/` microphone + STT (one-shot) + wakeword listener (tray-only)
- `app/brain/` orchestrator + parsing + routing
- `app/actions/` safe starter actions
- `app/output/` responder + TTS
- `app/core/` shared types/enums/state/logger
- `app/config/` settings/constants
- `app/services/` runtime container

## How To Run
From repo root:

Install dependencies:
- `pip install -r requirements.txt`

### Terminal (CLI)
- `python -m app.main`

### Tray (System Tray UI)
- `python -m app.main --tray`

Background start (best-effort on Windows):
- `python -m app.main --background`

Tray menu:
- Listen once
- Exit

## Voice (One-Shot)

Hotkey:
- While the app is running (CLI or tray), press `shift+v` to trigger one-shot listening (if hotkeys are available).
- Disable/change via `app/config/settings.py` (`hotkey_enabled`, `hotkey_combo`).

In the terminal app, type:
- `voice` (or `listen`)

When transcription succeeds, the app prints the transcript before processing it.

Wake word (tray mode only, optional):
- Enable in `app/config/settings.py`: set `wake_word_enabled=True`.
- Customize phrases via `wake_word_phrases` (default: `hey jarvis`, `jarvis`).
- When a wake phrase is detected, tray mode triggers the same one-shot listen -> STT -> assistant pipeline.

Voice dependencies:
- Uses `sounddevice` for microphone capture
- Uses `vosk` for offline speech-to-text

Vosk model:
- The app looks for a model via env vars `VOSK_MODEL_PATH` or `DESKTOP_CONTROL_AI_VOSK_MODEL`.
- Fallbacks:
  - `model/vosk-model-small-en-us-0.15`
  - first valid model folder inside `model/`

Voice capture tuning (optional):
- edit `app/config/settings.py` (`voice_max_seconds`, `voice_sample_rate_hz`, `voice_min_peak`, `voice_trailing_silence_seconds`, `voice_device_index`)

## TTS (Spoken Output)
- By default, assistant responses are printed and also spoken.
- TTS is implemented using Windows PowerShell + .NET `System.Speech` (offline/local).
- Disable or tune it by editing `app/config/settings.py` (`tts_enabled`, `tts_rate`).

## Supported Commands

Local (handled by terminal loop):
- `voice` / `listen` -> one-shot microphone input
- hotkey -> press `shift+v` to trigger one-shot listening (if enabled)
- `text` -> already in text mode
- `exit` / `quit` / `stop` -> exit

Assistant commands (text or transcribed voice):
- `help` / `?` / `h` -> prints command list
- `app help` / `browser help` / `system help` / `file help` -> prints a shorter section list
- `hello` / `hi` / `hey` -> greeting
- `time` -> prints current local time
- `date` -> prints today\'s date
- `what day is it` -> prints day of week
- `volume up` / `volume down` / `mute` -> safe volume controls (Windows)
- `open notepad` -> launches Notepad
- `open calculator` (or `open calc`) -> launches Calculator
- `open chrome` -> launches Chrome if found; otherwise opens default browser
- `open vscode` -> launches VS Code if found
- `open explorer` / `open file explorer` -> opens File Explorer
- `open settings` -> opens Windows Settings
- `open downloads` -> opens Downloads folder
- `open desktop` -> opens Desktop folder
- `open youtube` -> opens YouTube
- `open gmail` -> opens Gmail
- `search <query>` -> Google search in default browser
- `search google <query>` -> Google search
- `search youtube <query>` -> YouTube search
- `file <command>` -> limited safe navigation (try `file downloads` or `file desktop`)

## Notes On Gesture
Gesture is intentionally not part of the active runtime.
The goal is to stabilize the voice-first assistant foundation first.

## Roadmap (High-Level)
Next steps will focus on:
- wake word gating improvements (still lightweight)
- continuous listening/background listening
- improve transcription reliability and device handling
- expand safe action set (Windows-focused)
- add structured logging + config loading
- add tests and CI
- only then consider multimodal fusion / gesture re-integration

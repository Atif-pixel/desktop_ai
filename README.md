# Desktop Control AI (Windows 10/11)

Voice-first desktop assistant foundation for Windows.

## Purpose
Build a production-grade assistant that can control the desktop using voice (primary) and later gestures (secondary).

## Current Direction
- Voice-first architecture under `app/`
- Gesture code exists only as dormant legacy experiments under `gesture/` and `scripts/experiments/gesture/`
- No gesture runtime is active

## Current Status (Step 4)
- The assistant is runnable in **text-mode**.
- A controlled **one-shot voice input** path is available as a bridge before adding:
  - wakeword
  - continuous listening/background mode
- Basic **text-to-speech (TTS)** is available and will speak assistant responses while still printing them.

Text-mode remains the fallback and should keep working even if voice dependencies/models are missing.

## Architecture Overview
Text-mode and voice-mode share the same pipeline:

`input(text)` -> `intent` -> `orchestrator` -> `action` -> `response`

Voice-mode is currently one-shot:

`mic` -> `speech-to-text` -> `input(text)` -> (same pipeline)

Output (Step 4):
- responses are printed to the terminal
- and optionally spoken via TTS

Concrete runtime flow:
- `app/main.py` (terminal loop)
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
- `app/input/voice/` microphone + STT (one-shot) + wakeword interface (wakeword not used yet)
- `app/brain/` orchestrator + parsing + routing
- `app/actions/` safe starter actions
- `app/output/` responder + TTS
- `app/core/` shared types/enums/state/logger
- `app/config/` settings/constants
- `app/services/` runtime container

## How To Run
From repo root:

- `python -m app.main`

Install dependencies:
- `pip install -r requirements.txt`

### Voice (One-Shot)

Hotkey (Step 5A):
- While the app is running, press `shift+v` to trigger one-shot listening (if hotkeys are available).
- Disable/change via `app/config/settings.py` (`hotkey_enabled`, `hotkey_combo`).
In the terminal app, type:
- `voice` (or `listen`)

When transcription succeeds, the app prints the transcript before processing it.

Voice dependencies:
- Uses `sounddevice` for microphone capture
- Uses `vosk` for offline speech-to-text

Vosk model:
- Download a Vosk model and set `VOSK_MODEL_PATH` (or `DESKTOP_CONTROL_AI_VOSK_MODEL`) to the model directory.
- Example model: `vosk-model-small-en-us-0.15`

Voice capture tuning (optional):
- edit `app/config/settings.py` (`voice_max_seconds`, `voice_sample_rate_hz`, `voice_min_peak`, `voice_trailing_silence_seconds`, `voice_device_index`)

### TTS (Spoken Output)
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
- `hello` / `hi` / `hey` -> greeting
- `time` -> prints current local time
- `date` -> prints today's date
- `what day is it` -> prints day of week
- `volume up` / `volume down` / `mute` -> safe volume controls (Windows)
- `open notepad` -> launches Notepad
- `open calculator` (or `open calc`) -> launches Calculator
- `open chrome` -> launches Chrome if found; otherwise opens default browser
- `open vscode` -> launches VS Code if found
- `open explorer` -> opens File Explorer
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
- wakeword gating
- continuous listening/background runtime
- improve transcription reliability and device handling
- expand safe action set (Windows-focused)
- add structured logging + config loading
- add tests and CI
- only then consider multimodal fusion / gesture re-integration







# Desktop Control AI (Windows 10/11)

Voice-first desktop assistant foundation for Windows.

## Purpose
Build a production-grade assistant that can control the desktop using voice (primary) and later gestures (secondary).

## Current Direction
- Voice-first architecture under `app/`
- Gesture code exists only as dormant legacy experiments under `gesture/` and `scripts/experiments/gesture/`
- No gesture runtime is active

## Current Status (Step 3A)
- The assistant is runnable in **text-mode**.
- A controlled **one-shot voice input** path is available as a bridge before adding:
  - wakeword
  - continuous listening/background mode
  - text-to-speech

Text-mode remains the fallback and should keep working even if voice dependencies/models are missing.

## Architecture Overview
Text-mode and voice-mode share the same pipeline:

`input(text)` -> `intent` -> `orchestrator` -> `action` -> `response`

Voice-mode is currently one-shot:

`mic` -> `speech-to-text` -> `input(text)` -> (same pipeline)

Concrete runtime flow:
- `app/main.py` (terminal loop)
- `app/services/assistant_runtime.py` (runtime wiring + one-shot voice coordination)
- `app/brain/orchestrator.py` (coordinates brain pipeline)
- `app/brain/intent_parser.py` (deterministic parsing)
- `app/brain/command_router.py` (routes to actions)
- `app/actions/*` (does safe work or returns placeholder results)
- `app/output/responder.py` (builds final response)

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
- `app/output/` responder + TTS interface (placeholder)
- `app/core/` shared types/enums/state/logger
- `app/config/` settings/constants
- `app/services/` runtime container

## How To Run
From repo root:

- `python -m app.main`

Install dependencies:
- `pip install -r requirements.txt`

### Voice (One-Shot)
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

## Supported Commands

Local (handled by terminal loop):
- `voice` / `listen` -> one-shot microphone input
- `text` -> already in text mode
- `exit` / `quit` / `stop` -> exit

Assistant commands (text or transcribed voice):
- `help` / `?` / `h` -> prints command list
- `hello` / `hi` / `hey` -> greeting
- `time` -> prints current local time
- `open notepad` -> launches Notepad
- `open calculator` (or `open calc`) -> launches Calculator
- `open chrome` -> launches Chrome if found; otherwise opens default browser
- `search <query>` -> opens a browser search in the default browser
- `file <command>` -> placeholder (not implemented yet)

## Notes On Gesture
Gesture is intentionally not part of the active runtime.
The goal is to stabilize the voice-first assistant foundation first.

## Roadmap (High-Level)
Next steps will focus on:
- wakeword gating
- continuous listening/background runtime
- improve transcription reliability and device handling
- implement TTS under `app/output/`
- expand safe action set (Windows-focused)
- add structured logging + config loading
- add tests and CI
- only then consider multimodal fusion / gesture re-integration








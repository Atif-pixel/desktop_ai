# Desktop Control AI (Windows 10/11)

Voice-first desktop assistant foundation for Windows.

## Purpose
Build a production-grade assistant that can control the desktop using voice (primary) and later gestures (secondary).

## Current Direction
- Voice-first architecture under `app/`
- Gesture code exists only as dormant legacy experiments under `gesture/` and `scripts/experiments/gesture/`
- No gesture runtime is active

## Current Status (Step 2)
- The assistant is runnable in **text-mode** as a bridge before adding:
  - microphone capture
  - speech-to-text
  - wakeword
  - text-to-speech
- The goal right now is to validate the end-to-end pipeline and module boundaries.

## Architecture Overview
Text-mode today follows the same shape as voice-mode later:

`input(text)` ? `intent` ? `orchestrator` ? `action` ? `response`

Concrete runtime flow:
- `app/main.py` (terminal loop)
- `app/services/assistant_runtime.py` (runtime wiring)
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
- `app/input/voice/` microphone/STT/wakeword interfaces (placeholders)
- `app/brain/` orchestrator + parsing + routing
- `app/actions/` safe starter actions
- `app/output/` responder + TTS interface (placeholder)
- `app/core/` shared types/enums/state/logger
- `app/config/` settings/constants
- `app/services/` runtime container

## How To Run
From repo root:

- `python -m app.main`

Optional (dependencies):
- `pip install -r requirements.txt`

## Supported Commands (Text Mode)
Built-ins:
- `help` / `?` / `h` ? prints command list
- `hello` / `hi` / `hey` ? greeting
- `exit` / `quit` / `stop` ? exit

Real actions (safe starter set):
- `time` ? prints current local time
- `open notepad` ? launches Notepad
- `open calculator` (or `open calc`) ? launches Calculator
- `open chrome` ? launches Chrome if found; otherwise opens default browser
- `search <query>` ? opens a browser search in the default browser

Placeholders:
- `file <command>` ? returns a clear "not implemented yet" response

## Notes On Gesture
Gesture is intentionally not part of the active runtime during Step 2.
The goal is to stabilize the voice-first assistant foundation first.

## Roadmap (High-Level)
Next steps (Step 3+) will focus on:
- implement microphone capture + speech-to-text under `app/input/voice/`
- add wakeword gating (optional)
- implement TTS under `app/output/`
- expand safe action set (Windows-focused)
- add structured logging + config loading
- add tests and CI
- only then consider multimodal fusion / gesture re-integration

# STEP2A - Cleanup + Voice-First Structure

Date: 2026-04-06

## What cleanup was done
- Added `.gitignore` to ignore `venv/`, `__pycache__/`, `*.pyc`, and common dev artifacts.
- Replaced misspelled `requirenments.txt` with a proper `requirements.txt`.
- Moved ad-hoc experiment scripts out of project root into `scripts/` (see below).

## What structure was created
Created a voice-first application skeleton under `app/` with placeholder packages only:
- `app/` (entrypoint placeholders)
- `app/config/` (configuration placeholders)
- `app/core/` (shared types/utilities placeholders)
- `app/input/voice/` (voice input placeholder)
- `app/input/gesture/` (gesture input placeholder; intentionally inactive)
- `app/brain/` (planning/LLM logic placeholder; deferred)
- `app/actions/` (Windows actions placeholder; deferred)
- `app/output/` (TTS/UI output placeholder; deferred)
- `app/services/` (background services placeholder; deferred)
- `scripts/` (experiments / utilities)
- `tests/` (test package placeholder)

## What was left untouched
- Existing gesture modules in `gesture/` were not refactored or "fixed" in this step.
- No runtime logic, orchestrator, or gesture rework was implemented.

## How gesture was handled
- Gesture code remains in `gesture/` as legacy/dormant experiment code.
- Gesture is not wired into `app/` and is not part of the active runtime.
- Related interactive scripts were moved under `scripts/experiments/gesture/`.

## Intentionally deferred to next steps (Step 2B)
- Decide the real runtime entrypoint contract (`app/runner.py`) and execution model (foreground/background).
- Implement voice capture + transcription modules under `app/input/voice/`.
- Define command schema, routing, and an action execution layer under `app/actions/`.
- Add structured logging and configuration loading (env/config file) under `app/core/` + `app/config/`.
- Add tests and CI workflow.

## Notes on tracked generated files
This repo previously tracked generated files (notably `venv/` and `__pycache__/` artifacts).

Step 2A action taken:
- Removed `venv/` from git tracking (kept on disk): `git rm -r --cached venv`
- Removed `gesture/__pycache__/` artifacts from git tracking (kept on disk): `git rm -r --cached gesture/__pycache__`

`.gitignore` prevents them from being re-added.


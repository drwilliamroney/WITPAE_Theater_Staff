# WITPAE Theater Staff - Copilot Instructions

## Project scope

This repository is now a Python desktop application implemented with PyQt5.
The app is Windows-focused and targets Python 3.13+ x86 because game DLL
interop requires a 32-bit process.

## Pre-work review requirement

- Before beginning any implementation work, review `ANTIPATTERNS.md` and
  `CHANGELOG.md`.
- Treat `ANTIPATTERNS.md` as a hard guardrail list of repeated mistakes to
  avoid.
- Review `CHANGELOG.md` to maintain continuity and avoid reintroducing recently
  fixed regressions.

## Core constraints

- Python interpreter must be 32-bit and >= 3.13.
- `pwsdll.dll` and `pwsdll7.dll` must exist in the configured game directory.
- UI is currently map-first (base map and shell), with overlays introduced in
  incremental stages.
- Scraper-derived runtime data is in-memory only.
- Do not reintroduce JSON files, JSON dataset naming, or any disk-based fallback
  for overlay/runtime data when borrowing logic from legacy repos.
- If in-memory scraper data is missing, fail loudly or log that the snapshot is
  missing; do not silently fall back to JSON or placeholder data.

## Code style and architecture

- Follow Python 3 best practices:
  - Use type hints for all public functions and methods.
  - Prefer `pathlib.Path` over string path concatenation.
  - Keep functions small and cohesive.
  - Favor dataclasses for structured state.
  - Use explicit error handling and actionable exception messages.
- Organize logic by responsibility:
  - `app/main.py` for startup and CLI parsing.
  - `app/main_window.py` for UI shell and presentation wiring.
  - `app/map_assembly.py` for tile stitching logic.
  - `app/logging_setup.py` for logging policy.

## Logging policy

- Use the standard `logging` module.
- Configure Rich handler formatting via `rich.logging.RichHandler`.
- Use structured and concise log messages that include context (path, side,
  operation).
- Do not use `print` for runtime diagnostics outside startup scripts.

## Dependency policy

- Keep dependencies minimal and pinned in `requirements.txt`.
- Prefer batteries-included or widely adopted libraries.
- Verify Windows x86 and Python 3.13+ compatibility before adding packages.

## Testing guidance

- Prioritize tests for non-UI logic (`map_assembly`, coordinate transforms,
  argument parsing, and data helpers).
- Keep UI tests lightweight and focused on startup smoke behavior where needed.
- Before stating that implementation work is complete, run a startup smoke check
  via `run_ui.bat` or `run_ui.ps1` and verify the app does not exit with a
  compile/import/syntax startup error.
- If startup smoke check cannot be run in the current environment, explicitly
  report that limitation and do not claim full completion.

## Changelog maintenance

- Maintain `CHANGELOG.md` for all user-visible behavior changes, bug fixes,
  and feature additions.
- When implementation work is complete, add a concise changelog entry in
  Keep a Changelog style sections (`Added`, `Changed`, `Fixed`) under an
  `Unreleased` heading or the active release heading used by the repo.
- Do not mark work complete if code changed but `CHANGELOG.md` was not updated
  (unless the user explicitly asks to skip changelog updates).
- Changelog entries should be outcome-focused (what changed for users) and
  avoid internal-only implementation detail unless it affects behavior.

## Migration guidance

- Do not reintroduce .NET, WPF, solution files, or C# build scripts.
- Keep startup scripts (`run_ui.bat`, `run_ui.ps1`) as the canonical launch
  entry points for users.

## UI stability guardrails (do not regress)

- Preserve overlay controls as a left docked explorer-style panel in
  `app/main_window.py` (QDockWidget with grouped checkboxes).
- Do not move overlay visibility controls to the top toolbar unless the user
  explicitly asks for that change.
- Keep startup defaults for the overlay panel as:
  - Common section expanded.
  - `Regions` checked.
  - `HexGrid` checked.
  - Mode sections (for example Submarine) collapsed by default.
- Preserve grouped overlay structure:
  - Common: `hexgrid`, `regions`, `invasions`, `threats`, `combat`.
  - Submarine: `submarine_patrols`, `submarine_threats`.
- When editing UI code, do not remove `_init_overlays_dock`,
  `_create_overlay_section`, or `_set_overlay_layer_visible` unless explicitly
  instructed by the user.

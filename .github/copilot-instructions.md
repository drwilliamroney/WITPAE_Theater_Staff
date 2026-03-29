# WITPAE Theater Staff - Copilot Instructions

## Project scope

This repository is now a Python desktop application implemented with PyQt5.
The app is Windows-focused and targets Python 3.13+ x86 because game DLL
interop requires a 32-bit process.

## Core constraints

- Python interpreter must be 32-bit and >= 3.13.
- `pwsdll.dll` and `pwsdll7.dll` must exist in the configured game directory.
- UI is currently map-first (base map and shell), with overlays introduced in
  incremental stages.

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

## Migration guidance

- Do not reintroduce .NET, WPF, solution files, or C# build scripts.
- Keep startup scripts (`run_ui.bat`, `run_ui.ps1`) as the canonical launch
  entry points for users.

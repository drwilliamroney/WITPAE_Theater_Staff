# WITPAE Theater Staff

A local Windows desktop UI for War in the Pacific: Admiral's Edition.

This repository now targets a single-process Python architecture using PyQt5 and
32-bit Python 3.13 so game DLLs can be called in-process.

## Requirements

- Windows
- Python 3.13 **32-bit**
- Game installation directory containing:
  - `pwsdll.dll`
  - `pwsdll7.dll`

## Quick Start

### Batch launcher

```bat
run_ui.bat
```

### PowerShell launcher

```powershell
.\run_ui.ps1
```

Both launchers:

1. Verify Python is x86 and exactly 3.13
2. Verify required game DLLs are present in the provided game directory
3. Create `.venv` if needed
4. Install dependencies from `requirements.txt`
5. Start the PyQt5 UI

If Python x86 3.13 is not found, the script prints installation guidance.

Python 3.14 x86 is not currently supported because `PyQt5` wheels are not
available for this project target yet.

## Current UI Scope

- Main window title: `WITPAE Theater Staff`
- Base map assembled from `ART\WPEN00.bmp` to `ART\WPEN41.bmp`
- Placeholder map fallback when tiles are missing
- Regions overlay from pywitpaeui theater boundaries with toolbar toggle
- HexGrid overlay (interconnected hex-cell grid) with toolbar toggle

## Project Structure

```text
app/
  main.py            # App startup and CLI parsing
  main_window.py     # Main PyQt5 window and map display shell
  map_assembly.py    # Tile stitching and placeholder generation
  logging_setup.py   # Rich logging configuration
run_ui.bat           # Windows cmd launcher with environment checks
run_ui.ps1           # PowerShell launcher with environment checks
requirements.txt     # Pinned Python dependencies
```

## Logging

Runtime logging uses Python `logging` with `rich.logging.RichHandler` for
readable console output.

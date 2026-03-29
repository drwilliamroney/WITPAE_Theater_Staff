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

## Map and Hex Calibration

Hex calibration is based on direct measurement from the game-provided
`ART\WPEH00.bmp` reference map rather than visual nudging.

### Calibration approach

1. Load `WPEH00.bmp` as grayscale.
2. Compute horizontal and vertical edge-energy profiles using first
  differences (`abs(diff)`) across pixels.
3. Run lag autocorrelation on each profile over expected spacing ranges:
  - X lag search: 30 to 60 px
  - Y lag search: 25 to 55 px
4. Select the strongest correlation peaks as center-to-center spacing.
5. Cross-check nearby peaks to ensure the result is stable (not a single
  outlier peak).

This method was run with NumPy for reliable and repeatable numeric analysis.

### Final measured spacing

- Horizontal spacing (X): **42 px**
- Vertical spacing (Y): **38 px**

Top peak neighborhoods were consistent around those values:

- X peaks clustered around 41 to 43 px, with 42 px dominant.
- Y peaks clustered around 37 to 39 px, with 38 px dominant.

### Locked implementation values

The runtime constants are locked to the following values in
`app/main_window.py`:

- `HEX_STEP_X = 42.0`
- `HEX_STEP_Y = 38.0`
- `HEX_CENTER_X_1_1 = 24.0`
- `HEX_CENTER_Y_1_1 = 8.0`
- `HEX_ANCHOR_ADJUST_X = 19.0`
- `HEX_ANCHOR_ADJUST_Y = 17.0`
- `SHIFT_EVEN_ROWS_RIGHT = True`

These were spot-checked across multiple locations and are typically within
about 1 to 2 pixels.

Do not adjust these constants by visual nudging. If a future change is needed,
rerun the `WPEH00.bmp` measurement workflow first and then apply a single,
documented recalibration update.

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

# WITPAE Theater Staff — Copilot Instructions

## Project Overview

This is a single, fully integrated Windows 11+ desktop application for **War in the Pacific:
Admiral's Edition** game management.  It replaces a two-process legacy pair
(`pywitpaescraper` + `pywitpaeui`) with a unified 32-bit Python tkinter GUI that loads game
data directly via the game's 32-bit C DLLs (`pwsdll.dll` / `pwsdll7.dll`).

## Architecture

```
src/witpae_theater_staff/
├── main.py                  # Entry point: main() creates AppWindow
├── app_window.py            # Root tkinter.Tk window (toolbar + map + detail)
├── dll_interface/
│   ├── __init__.py
│   └── pwsdll.py            # ctypes DLL wrapper (32-bit only; graceful fallback)
├── data/
│   ├── __init__.py
│   ├── models.py            # Dataclasses for game entities (ships, air groups, …)
│   ├── scraper.py           # Extracts game state via PWSDll → populates models
│   └── turn_watcher.py      # Background thread that watches save files for new turns
├── ui/
│   ├── __init__.py
│   ├── map_assembly.py      # Assembles BMP map tiles (Pillow); placeholder fallback
│   ├── coordinate_transform.py  # Game hex ↔ pixel (respects current zoom + pan)
│   ├── overlays.py          # Builds overlay data from game models
│   ├── map_canvas.py        # tkinter Canvas: map image + overlay items, zoom, pan
│   ├── tooltip.py           # Hover tooltip toplevel widget
│   ├── detail_panel.py      # Right-side Treeview detail panel
│   └── toolbar.py           # Top toolbar (side, turn info, overlay toggles)
└── config/
    ├── __init__.py
    └── settings.py          # JSON-persisted app settings; settings dialog
tests/
run_gui.bat                  # 32-bit Python venv bootstrap and launcher
requirements.txt
pyproject.toml
```

## Key Constraints

* **32-bit Python 3.10+** — required so ctypes can load the 32-bit game DLLs.
  The launcher (`run_gui.bat`) selects a 32-bit interpreter via `py -3-32`.
* **tkinter / ttk** — the *only* GUI toolkit used.  All layouts use `.grid()`.
  Do **not** use `.pack()` or `.place()`.
* **Pillow** — the *only* third-party dependency (map image assembly / resize).
* **No browser, no FastAPI, no subprocess scraper** — everything runs in-process.
* **Windows 11+** — target OS; DLL paths are Windows paths.  The code must still
  import cleanly on other platforms (for CI), but DLL loading is guarded with a
  graceful `DllNotAvailableError`.

## Coding Conventions

* Python 3.10+ syntax; use `match`/`case`, `|` union types, `dataclasses`.
* All public functions and classes must have docstrings.
* Logging via the standard `logging` module; use `logging.getLogger(__name__)`.
* Avoid global mutable state; pass dependencies explicitly.
* Use `pathlib.Path` for all filesystem operations.
* Guard DLL-specific code behind `try/except OSError` so tests pass on Linux/CI.
* Tests live in `tests/`; run with `pytest`.

## Overlay Layer Tags (tkinter Canvas)

Each overlay type is assigned a unique Canvas tag so it can be shown/hidden
atomically with `canvas.itemconfigure(tag, state="normal"/"hidden")`:

| Tag              | Content                               |
|------------------|---------------------------------------|
| `overlay_region` | Theater region polygons               |
| `overlay_tf`     | Task force movement arrows            |
| `overlay_ship`   | Individual ship dots                  |
| `overlay_base`   | Base circles with supply health color |
| `overlay_air`    | Air-group dots + search/ASW arcs      |
| `overlay_land`   | Ground unit markers                   |
| `overlay_threat` | Threat hex heat-map cells             |

## Coordinate System

Game uses a 232 × 205 hex grid (1-indexed).  The transform in
`coordinate_transform.py` maps hex → pixel with a configurable zoom/pan offset.
All point overlays use *hex-center*; region polygon vertices use *hex top-left*.

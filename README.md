# WITPAE Theater Staff

A **32-bit Windows desktop application** for players of
**War in the Pacific Admiral's Edition (WitPAE)** — a turn-based hex-coordinate
strategy game covering World War 2 across the entire Pacific Theater.

The tool reads the game's native save files **directly** via the game's own
32-bit DLL and presents the extracted data as an interactive map with
toggleable information overlays — think traditional paper maps with acetate
sheets layered on top.

---

## Technology

| Component | Choice | Reason |
|---|---|---|
| Language | **Python 3.11 (32-bit / x86)** | Must match the 32-bit game DLL |
| GUI | **wxPython 4.2.5** | Only actively-maintained framework with 32-bit PyPI wheels for Python 3.10+ |
| Rendering | `wx.GraphicsContext` | Full RGBA alpha transparency for overlay layers |
| Map image | **Pillow** | Assembles the 7 × 6 game BMP art tiles |
| DLL binding | `ctypes` (stdlib) | In-process call to `pwsdll.dll` — no subprocess, no browser |

> tkinter is not used — it lacks true alpha transparency required for the
> semi-transparent overlay layers.
>
> PySide6 / PyQt6 are not used — Qt 6 has no 32-bit Windows support.
>
> There is no web server and no browser window.  Everything runs in a single
> 32-bit Python process.

See [`docs/technology-comparison.md`](docs/technology-comparison.md) for the
full analysis including all options considered and why each was accepted or
rejected.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.10–3.13 (32-bit / x86)** | Download the *Windows installer (32-bit)* from <https://www.python.org/downloads/windows/>. Python 3.9 is not supported (EOL Oct 2025 and incompatible with wxPython 4.2.5). |
| **War in the Pacific Admiral's Edition** | Installed locally (provides `pwsdll.dll`, `pwsdll7.dll`, and art tiles). |
| **Git** | Must be on `PATH` so `run_gui.bat` can pull updates. |

> **Why 32-bit Python?**
> The game DLL (`pwsdll.dll`) is a 32-bit (x86) binary.  A 64-bit process
> cannot load a 32-bit DLL into the same address space.  There is no
> subprocess workaround — the application calls the DLL directly for
> performance and simplicity.

---

## Quick Start (Windows)

```bat
run_gui.bat
```

The launcher will automatically:

1. Verify a 32-bit Python 3.10–3.13 interpreter is available
2. Run `git pull` to fetch the latest code
3. Create (or reuse) a `.venv` virtual environment
4. Install / update `wxPython`, `Pillow`, and `rich` from `requirements.txt`
   *(first run downloads ~130 MB — this is normal)*
5. Launch the application

---

## Project Layout

```
WITPAE_Theater_Staff/
├── .github/
│   └── copilot-instructions.md    # Coding conventions and architecture guidelines
├── docs/
│   └── technology-comparison.md   # Full analysis of technology options
├── src/
│   └── witpae_theater_staff/
│       ├── __init__.py
│       ├── main.py                # wx.App entry point
│       ├── dll/                   # ctypes DLL wrapper (ported from pywitpaescraper)
│       ├── models/                # Active data models
│       ├── map/                   # Coordinate transform + map assembly
│       ├── overlays/              # Overlay layer implementations
│       └── ui/                    # wx widgets: frame, map panel, layer panel, info panel
├── tests/                         # pytest unit tests
├── requirements.txt               # Pinned dependencies
└── run_gui.bat                    # Windows launcher
```

---

## Development

```bat
:: Activate the virtual environment (after running run_gui.bat at least once)
.venv\Scripts\activate

:: Run the app directly
python src\witpae_theater_staff\main.py

:: Run tests
pytest tests\
```

See `.github/copilot-instructions.md` for coding conventions, wxPython
patterns, overlay architecture, and DLL integration rules.

---

## Reference Repositories

These companion repos were built with an earlier architecture (browser-based,
split-process) and are used here as **reference documentation only** — not
runtime dependencies:

| Repo | What it contributes |
|---|---|
| [pywitpaescraper](https://github.com/drwilliamroney/pywitpaescraper) | DLL struct definitions, data models, extraction logic |
| [pywitpaeui](https://github.com/drwilliamroney/pywitpaeui) | Coordinate transform, overlay geometry and colour palettes, map assembly |

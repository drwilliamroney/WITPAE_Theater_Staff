# WITPAE Theater Staff

A 32-bit Windows desktop GUI application to assist players of
**War in the Pacific Admiral's Edition (WitPAE)** — a turn-based hex-coordinate
strategy game covering World War 2 across the entire Pacific Theater.

Players take either the **Japanese** side (IJArmy / IJNavy) or the **Allied** side
(all other nations and forces defined in the game database).

---

## GUI Library

The application uses Python's built-in **`tkinter`** library (with `ttk` themed
widgets). `tkinter` ships with every standard Python installer on Windows, requires
no extra packages, and its `Canvas` widget is well suited to the hex-grid map
rendering that will be added in later iterations.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.9 – 3.13 (32-bit / x86)** | Download the *Windows installer (32-bit)* from <https://www.python.org/downloads/windows/> |
| **Git** | Must be on `PATH` so `run_gui.bat` can pull updates |

> **Why 32-bit?**  WitPAE itself is a 32-bit application and any future
> in-process integration or shared-memory work requires matching bitness.

---

## Quick Start (Windows)

```bat
run_gui.bat
```

The launcher will automatically:

1. Verify a 32-bit Python 3 interpreter is available  
2. Run `git pull` to fetch the latest code  
3. Create (or reuse) a `.venv` virtual environment  
4. Install / update dependencies from `requirements.txt`  
5. Launch the application  

---

## Project Layout

```
WITPAE_Theater_Staff/
├── .github/
│   └── copilot-instructions.md   # Repo-level Copilot / coding guidelines
├── src/
│   └── witpae_theater_staff/
│       ├── __init__.py
│       └── main.py               # Application entry point
├── requirements.txt
├── run_gui.bat                   # Windows launcher
└── README.md
```

---

## Development

```bat
:: Activate the virtual environment (after running run_gui.bat at least once)
.venv\Scripts\activate

:: Run the app directly
python src\witpae_theater_staff\main.py
```

See `.github/copilot-instructions.md` for coding conventions and domain vocabulary.
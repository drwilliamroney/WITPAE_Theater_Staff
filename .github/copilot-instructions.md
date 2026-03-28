# Copilot Instructions for WITPAE Theater Staff

## Project Overview

**WITPAE Theater Staff** is a Python desktop application that helps manage theater staff scheduling and assignments. The application provides a graphical user interface (GUI) built with Python's `tkinter`/`ttk` toolkit.

- **Language:** Python
- **GUI Framework:** `tkinter` with `ttk` themed widgets
- **Layout Manager:** `.grid()` — always use `.grid()` for widget placement; do not mix `.pack()` or `.place()`
- **Target runtime:** 32-bit Python (for Windows compatibility), running inside a virtual environment (`venv`)

## Repository Layout

```
WITPAE_Theater_Staff/
├── .github/
│   └── copilot-instructions.md   # This file
├── src/
│   └── witpae_theater_staff/
│       └── main.py               # Application entry point; contains main()
├── run_gui.bat                   # Windows launcher (uses 32-bit Python venv)
├── .gitignore                    # Standard Python gitignore
├── LICENSE
└── README.md
```

> **Note:** The `src/` directory follows a standard Python `src`-layout. The application package lives under `src/witpae_theater_staff/`.

## Running the Application

On **Windows**, launch the GUI via:

```bat
run_gui.bat
```

This script activates the 32-bit Python virtual environment and runs `src/witpae_theater_staff/main.py`.

To run manually (after activating the venv):

```bash
python src/witpae_theater_staff/main.py
```

## Coding Conventions

- **Entry point:** `main()` function in `src/witpae_theater_staff/main.py`
- **Widget layout:** Always use `.grid()`. Never use `.pack()` or `.place()`.
- **Imports:** Use `import tkinter as tk` and `from tkinter import ttk`.
- **Style:** Follow [PEP 8](https://peps.python.org/pep-0008/) for all Python code.
- **Naming:** Use `snake_case` for variables and functions; `PascalCase` for classes.
- **Dependencies:** Add new Python dependencies to `requirements.txt` (if present) and document any special installation needs.
- **No external GUI frameworks** (e.g., Qt, wx): stick to `tkinter`/`ttk` only.

## Build & Validation

There is currently no automated CI pipeline. To validate changes:

1. Activate the virtual environment.
2. Run the application: `python src/witpae_theater_staff/main.py`
3. Visually confirm the GUI launches and behaves correctly.
4. Run any tests present in the `tests/` directory (if they exist):
   ```bash
   python -m pytest tests/
   ```

## Key Notes for Coding Agents

- Trust the information in this file. Only search the codebase if information here seems incomplete or incorrect.
- The virtual environment directory is excluded from version control (`.venv`, `venv/`, `env/`).
- When adding new windows or dialogs, always inherit from `tk.Toplevel` and use `.grid()` for layout.
- The app is designed for Windows; avoid platform-specific code that would break on Windows.

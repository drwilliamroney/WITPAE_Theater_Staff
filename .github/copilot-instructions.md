# GitHub Copilot Instructions — WITPAE Theater Staff

## Project Context

WITPAE Theater Staff is a 32-bit Windows desktop GUI application that assists players of
**War in the Pacific Admiral's Edition (WitPAE)**, a turn-based hex-coordinate strategy game
covering World War 2 across the entire Pacific Theater. Players take either the Japanese side
(IJArmy / IJNavy) or the Allied side (all other nations/forces defined in the game database).

The application is written in **Python 3 (32-bit)** using the built-in `tkinter` GUI library.

---

## Python 3 Best Practices

### Code Style
- Follow **PEP 8** for all code style (4-space indentation, 88-char line limit for code, 72 for docstrings).
- Follow **PEP 257** for docstring conventions — use triple double-quoted strings.
- Use **type hints** (PEP 484 / PEP 526) on all public functions, methods, and class attributes.
- Use **f-strings** (PEP 498) for string formatting; avoid `%` formatting or `.format()`.
- Prefer `pathlib.Path` over `os.path` for file system operations.
- Use `dataclasses` or `NamedTuple` for simple data-holding classes.
- Use `enum.Enum` for named constants / flag sets.

### Project Structure
- Application source lives under `src/witpae_theater_staff/`.
- The entry point is `src/witpae_theater_staff/main.py` with a `main()` function guarded by
  `if __name__ == "__main__": main()`.
- Keep GUI code, business logic, and data models in separate modules.

### Imports
- Use absolute imports; avoid relative imports except within the same package.
- Group imports in the order: standard library → third-party → local, separated by blank lines.

### Error Handling
- Catch specific exceptions; never use a bare `except:`.
- Log errors with the `logging` module (not `print`).

### Testing
- Write tests with `pytest`.
- Keep tests under the `tests/` directory, mirroring the `src/` layout.
- Aim for unit-testable business logic decoupled from the GUI layer.

### Dependencies
- Pin all third-party dependencies in `requirements.txt` using `==` version specifiers.
- The virtual environment is created and managed by `run_gui.bat`; never commit the `.venv/` folder.

### Git
- Write clear, imperative commit messages (e.g. "Add hex-grid canvas widget").
- Never commit secrets, credentials, or generated/compiled files (see `.gitignore`).

---

## GUI Conventions (tkinter)

- Use `ttk` themed widgets (`tkinter.ttk`) in preference to classic `tk` widgets.
- Lay out widgets with `.grid()` rather than `.pack()` or `.place()` to enable predictable,
  resizable layouts.
- Configure `columnconfigure` / `rowconfigure` with `weight=1` on resizable containers.
- The main window title must always be **"WITPAE Theater Staff"**.

---

## Domain Vocabulary

| Term | Meaning |
|------|---------|
| hex / hex coord | A single hexagonal cell on the WitPAE map grid, identified by (col, row) |
| IJArmy / IJNavy | Imperial Japanese Army / Imperial Japanese Navy |
| Allied | All non-Japanese forces (US, UK, ANZAC, Dutch, Chinese, etc.) |
| LCU | Land Combat Unit |
| TF | Task Force (naval) |
| Base | A named location that can be a supply hub, airfield, or port |

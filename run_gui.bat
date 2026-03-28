@echo off
REM ============================================================
REM  run_gui.bat — WITPAE Theater Staff launcher
REM
REM  Requirements:
REM    A 32-bit Python 3.10+ interpreter reachable as  py -3-32
REM    (install from https://www.python.org/downloads/windows/
REM     and check "Use the Python Launcher for Windows")
REM ============================================================

setlocal EnableDelayedExpansion

set VENV_DIR=%~dp0.venv32

REM ── 1. Locate a 32-bit interpreter ───────────────────────────────────────
where py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python Launcher ^(py.exe^) not found.
    echo         Install Python 3.10+ ^(32-bit^) from https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

py -3-32 -c "import sys; sys.exit(0 if sys.maxsize < 2**32 else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No 32-bit Python 3 interpreter found.
    echo         Install a 32-bit Python 3.10+ from https://www.python.org/downloads/windows/
    echo         and ensure it is registered with the Python Launcher.
    pause
    exit /b 1
)

REM ── 2. Bootstrap virtual environment ─────────────────────────────────────
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Creating 32-bit virtual environment in %VENV_DIR% ...
    py -3-32 -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM ── 3. Install / upgrade dependencies ────────────────────────────────────
echo [INFO] Installing dependencies ...
"%VENV_DIR%\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%VENV_DIR%\Scripts\python.exe" -m pip install --quiet -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

REM ── 4. Install the package in editable mode ───────────────────────────────
"%VENV_DIR%\Scripts\python.exe" -m pip install --quiet -e "%~dp0."
if errorlevel 1 (
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)

REM ── 5. Launch the GUI ────────────────────────────────────────────────────
echo [INFO] Launching WITPAE Theater Staff ...
"%VENV_DIR%\Scripts\python.exe" -m witpae_theater_staff.main %*

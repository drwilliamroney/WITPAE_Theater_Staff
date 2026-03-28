@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: run_gui.bat — WITPAE Theater Staff launcher
::
:: 1. Locates a 32-bit (x86) Python 3.10–3.13 interpreter
::    (wxPython 4.2.5 requires Python 3.10+; Python 3.9 is EOL Oct 2025)
:: 2. Performs a git pull to get the latest code
:: 3. Creates / reuses a .venv virtual environment
:: 4. Installs / updates dependencies from requirements.txt
::    (wxPython 4.2.5 + Pillow 12.x — both have win32 wheels on PyPI)
:: 5. Starts the application
:: ============================================================================

set SCRIPT_DIR=%~dp0

:: ── Step 1: Find a 32-bit Python 3.10–3.13 interpreter ──────────────────────
echo [1/4] Checking for a 32-bit Python 3.10–3.13 interpreter...

set PYTHON32=

:: Check common per-user 32-bit installation paths (prefer newer versions)
for %%V in (313 312 311 310) do (
    for %%P in (
        "%LocalAppData%\Programs\Python\Python%%V-32\python.exe"
        "%ProgramFiles(x86)%\Python%%V\python.exe"
    ) do (
        if "!PYTHON32!"=="" if exist %%P (
            set PYTHON32=%%P
        )
    )
)

:: Fall back to whatever "python" is on PATH — accept only if 32-bit AND >=3.10
if "!PYTHON32!"=="" (
    where python >nul 2>&1
    if !errorlevel! == 0 (
        python -c "import struct, sys; ok = struct.calcsize('P')*8==32 and sys.version_info>=(3,10); sys.exit(0 if ok else 1)" >nul 2>&1
        if !errorlevel! == 0 (
            set PYTHON32=python
        )
    )
)

if "!PYTHON32!"=="" (
    echo.
    echo  ERROR: No 32-bit ^(x86^) Python 3.10–3.13 interpreter found.
    echo.
    echo  wxPython 4.2.5 requires Python 3.10 or later ^(32-bit^).
    echo  Python 3.9 is NOT supported ^(end-of-life Oct 2025^).
    echo.
    echo  Install a 32-bit Python 3.11 or 3.12 release from:
    echo    https://www.python.org/downloads/windows/
    echo  Select the "Windows installer (32-bit)" option.
    echo.
    pause
    exit /b 1
)

echo  Found: !PYTHON32!
!PYTHON32! -c "import sys; print(' Version:', sys.version)"

:: ── Step 2: Git pull ─────────────────────────────────────────────────────────
echo.
echo [2/4] Pulling latest changes from git...
cd /d "%SCRIPT_DIR%"
git pull
if !errorlevel! neq 0 (
    echo  WARNING: git pull failed. Continuing with existing code.
)

:: ── Step 3: Create / reuse virtual environment ───────────────────────────────
echo.
echo [3/4] Setting up virtual environment...
set VENV_DIR=%SCRIPT_DIR%.venv

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo  Creating new virtual environment at %VENV_DIR% ...
    !PYTHON32! -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo  Reusing existing virtual environment.
)

call "%VENV_DIR%\Scripts\activate.bat"

:: ── Step 4: Install / update dependencies ────────────────────────────────────
echo.
echo [4/4] Installing dependencies...
echo  ^(wxPython 4.2.5 is ~130 MB — first install may take a few minutes^)
python -m pip install --upgrade pip --quiet
pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
if !errorlevel! neq 0 (
    echo  ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo  Dependencies up to date.

:: ── Launch the application ────────────────────────────────────────────────────
echo.
echo  Starting WITPAE Theater Staff...
echo.
python "%SCRIPT_DIR%src\witpae_theater_staff\main.py"

endlocal

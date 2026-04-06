@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

rem ================================================================
rem run_ui_dev.bat — WITPAE Theater Staff (PyQt5) — Development Build
rem
rem Lists available remote branches and asks the user to select one.
rem For the stable/main branch use run_ui.bat instead.
rem
rem Launch flow:
rem   0) Fetch remote branches, let user pick one, then pull
rem   1) Find Python 3.13 x86 interpreter
rem   2) Validate game DLL presence
rem   3) Create/update .venv and install dependencies
rem   4) Run the UI
rem ================================================================

set "DEFAULT_SIDE=allies"
set "DEFAULT_GAME_PATH=C:\Matrix Games\War in the Pacific Admiral's Edition"
set "PYTHON_EXE="
set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "GAME_DLL_1=pwsdll.dll"
set "GAME_DLL_2=pwsdll7.dll"
set "SELECTED_BRANCH=copilot/dev"

goto main

:git_update
where git >nul 2>&1
if errorlevel 1 (
    echo [WARN] git not found in PATH — skipping repository update.
    exit /b 0
)
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [WARN] Not inside a git repository — skipping repository update.
    exit /b 0
)

git fetch --prune origin >nul 2>&1
if errorlevel 1 (
    echo [WARN] git fetch failed — continuing with existing local code.
    exit /b 0
)

echo.
echo Available remote branches:
set /a BRANCH_COUNT=0
for /f "tokens=1" %%B in ('git branch -r 2^>nul ^| findstr /v "HEAD"') do (
    set "RAW=%%B"
    set "BNAME=!RAW:origin/=!"
    set /a BRANCH_COUNT+=1
    set "BRANCH_!BRANCH_COUNT!=!BNAME!"
    echo   !BRANCH_COUNT!. !BNAME!
)

if !BRANCH_COUNT!==0 (
    echo [WARN] No remote branches found — continuing with existing local code.
    exit /b 0
)

echo.
set "SEL=1"
set /p "SEL=Select branch # (1-!BRANCH_COUNT!, default 1): "
if "!SEL!"=="" set "SEL=1"

set /a SEL_NUM=!SEL! 2>nul
if !SEL_NUM! LSS 1 (
    echo [WARN] Invalid selection — using #1.
    set "SEL_NUM=1"
)
if !SEL_NUM! GTR !BRANCH_COUNT! (
    echo [WARN] Invalid selection — using #1.
    set "SEL_NUM=1"
)

for /l %%I in (1,1,!BRANCH_COUNT!) do (
    if %%I==!SEL_NUM! set "SELECTED_BRANCH=!BRANCH_%%I!"
)

echo [INFO] Switching to branch '!SELECTED_BRANCH!'...
git checkout !SELECTED_BRANCH! >nul 2>&1
if errorlevel 1 (
    echo [WARN] git checkout !SELECTED_BRANCH! failed — continuing with existing local code.
    exit /b 0
)
git pull --ff-only origin !SELECTED_BRANCH!
if errorlevel 1 (
    echo [WARN] git pull --ff-only origin !SELECTED_BRANCH! failed — continuing with existing local code.
    echo [WARN] (This may be due to local uncommitted changes or a non-linear history.)
)
exit /b 0

:check_game_dlls
set "MISSING_DLLS=0"

if exist "!GAME_PATH!\!GAME_DLL_1!" (
    echo [INFO] !GAME_DLL_1! detected
) else (
    echo [ERROR] !GAME_DLL_1! NOT detected
    set "MISSING_DLLS=1"
)

if exist "!GAME_PATH!\!GAME_DLL_2!" (
    echo [INFO] !GAME_DLL_2! detected
) else (
    echo [ERROR] !GAME_DLL_2! NOT detected
    set "MISSING_DLLS=1"
)

if "!MISSING_DLLS!"=="1" (
    echo.
    echo [ERROR] Required game DLLs were not found in:
    echo         !GAME_PATH!
    echo         Aborting launch.
    exit /b 1
)
exit /b 0

:print_python_info
echo [INFO] Python executable: %PYTHON_EXE%
"%PYTHON_EXE%" -c "import struct,sys; print('[INFO] Python version   :', sys.version.split()[0]); print('[INFO] Python architecture:', str(struct.calcsize('P')*8) + '-bit')"
if errorlevel 1 (
    echo [WARN] Failed to query Python runtime details.
)
exit /b 0

:validate_python
"%~1" -c "import struct,sys; raise SystemExit(0 if (sys.version_info[:2] == (3, 13) and struct.calcsize('P') * 8 == 32) else 1)" >nul 2>&1
if errorlevel 1 exit /b 1
set "PYTHON_EXE=%~1"
exit /b 0

:find_python
if exist "%VENV_PY%" (
    call :validate_python "%VENV_PY%"
    if not errorlevel 1 goto :eof
)

for %%P in ("py -3.13-32" "python") do (
    for /f "tokens=*" %%E in ('%%~P -c "import sys; print(sys.executable)" 2^>nul') do (
        call :validate_python "%%~E"
        if not errorlevel 1 goto :eof
    )
)

echo.
echo [ERROR] Python x86 3.13 was not found.
echo.
echo Install instructions:
echo   1) Download Python 3.13 Windows installer (32-bit):
echo      https://www.python.org/downloads/windows/
echo   2) Run installer and enable "Add python.exe to PATH".
echo   3) Re-run this script.
echo.
echo Quick launcher check command after install:
echo   py -3.13-32 -c "import struct,sys; print(sys.version); print(struct.calcsize('P')*8)"
exit /b 1

:ensure_venv
echo [INFO] Preparing Python environment...
if exist "%VENV_PY%" (
    call :validate_python "%VENV_PY%"
    if errorlevel 1 (
        echo [WARN] Existing .venv is not Python 3.13 x86. Rebuilding .venv ...
        rmdir /s /q "%VENV_DIR%"
        if errorlevel 1 (
            echo [ERROR] Failed to remove existing .venv directory.
            exit /b 1
        )
    )
)

if not exist "%VENV_PY%" (
    echo [INFO] Creating virtual environment at .venv ...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv.
        exit /b 1
    )
)

"%VENV_PY%" -m pip install --upgrade pip >nul
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip in .venv.
    exit /b 1
)

echo [INFO] Installing dependencies...
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)

"%VENV_PY%" -c "import PyQt5, PIL, rich" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python dependencies are not importable in this environment.
    echo         WITPAE Theater Staff currently requires Python 3.13 x86 for PyQt5.
    echo         Remove .venv and re-run with a Python 3.13-32 install.
    exit /b 1
)
exit /b 0

:main

rem -- 0. Fetch remote branches, ask user to pick one, then pull ------------
call :git_update

rem -- 1. Find Python --------------------------------------------------------
call :find_python
if errorlevel 1 (
    pause
    exit /b 1
)

rem -- 2. Prompt for side ---------------------------------------------------
echo.
set "RUN_SIDE="
set /p "RUN_SIDE=Run as [allies/japan] (default: %DEFAULT_SIDE%): "
if "!RUN_SIDE!"=="" set "RUN_SIDE=%DEFAULT_SIDE%"
if /I not "!RUN_SIDE!"=="allies" if /I not "!RUN_SIDE!"=="japan" (
    echo   Invalid value "!RUN_SIDE!" - using default: %DEFAULT_SIDE%
    set "RUN_SIDE=%DEFAULT_SIDE%"
)

rem -- 3. Prompt for game directory -----------------------------------------
set "GAME_PATH="
set /p "GAME_PATH=Game / save directory path (default: %DEFAULT_GAME_PATH%): "
if "!GAME_PATH!"=="" set "GAME_PATH=%DEFAULT_GAME_PATH%"

rem Save path is always <GAME_PATH>\SAVE
set "SAVE_PATH=!GAME_PATH!\SAVE"

echo.
call :check_game_dlls
if errorlevel 1 (
    pause
    exit /b 1
)

call :print_python_info

call :ensure_venv
if errorlevel 1 (
    pause
    exit /b 1
)

rem -- 4. Launch the application --------------------------------------------
echo.
echo [INFO] Starting WITPAE Theater Staff (!SELECTED_BRANCH!) ...
echo        Side      : !RUN_SIDE!
echo        Game dir  : !GAME_PATH!
echo        Save dir  : !SAVE_PATH!
echo        Python    : !PYTHON_EXE!
echo.

"%VENV_PY%" -m app.main --side "!RUN_SIDE!" --game-path "!GAME_PATH!" --save-path "!SAVE_PATH!"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] App exited with code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%

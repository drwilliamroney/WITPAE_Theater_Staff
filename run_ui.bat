@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

rem ============================================================
rem  run_ui.bat — WITPAE Theater Staff launcher
rem
rem  Prompts for game configuration, builds the x86 Release
rem  binary if needed, then launches the WPF application.
rem
rem  Requirements:
rem    .NET 8 SDK (x86 capable) — https://dotnet.microsoft.com/download
rem    Visual Studio 2022 Community is recommended but not required
rem    to build; the SDK alone is sufficient.
rem
rem  Default game path mirrors pywitpaeui convention:
rem    C:\Matrix Games\War in the Pacific Admiral's Edition
rem ============================================================

set "DEFAULT_SIDE=allies"
set "DEFAULT_GAME_PATH=C:\Matrix Games\War in the Pacific Admiral's Edition"
set "EXE_PATH=%~dp0src\WitpaeTheaterStaff\bin\Release\net8.0-windows\x86\WitpaeTheaterStaff.exe"

rem ── 1. Verify .NET SDK is available ──────────────────────────────────────
where dotnet >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] .NET SDK was not found on PATH.
    echo         Install .NET 8 SDK from https://dotnet.microsoft.com/download
    echo         and ensure it is on your PATH, then re-run this script.
    echo.
    pause
    exit /b 1
)

rem Quick version check (need 8.x)
for /f "tokens=1" %%v in ('dotnet --version 2^>nul') do set "DOTNET_VER=%%v"
if "%DOTNET_VER:~0,1%" neq "8" (
    echo.
    echo [WARNING] .NET %DOTNET_VER% detected; .NET 8 is recommended.
    echo           The build may still succeed, but results are untested.
    echo.
)

rem ── 2. Prompt for side ───────────────────────────────────────────────────
echo.
set "RUN_SIDE="
set /p "RUN_SIDE=Run as [allies/japan] (default: %DEFAULT_SIDE%): "
if "!RUN_SIDE!"=="" set "RUN_SIDE=%DEFAULT_SIDE%"
if /I not "!RUN_SIDE!"=="allies" if /I not "!RUN_SIDE!"=="japan" (
    echo   Invalid value "!RUN_SIDE!" — using default: %DEFAULT_SIDE%
    set "RUN_SIDE=%DEFAULT_SIDE%"
)

rem ── 3. Prompt for game directory ─────────────────────────────────────────
set "GAME_PATH="
set /p "GAME_PATH=Game / save directory path (default: %DEFAULT_GAME_PATH%): "
if "!GAME_PATH!"=="" set "GAME_PATH=%DEFAULT_GAME_PATH%"

rem Derive default save path as <GAME_PATH>\SAVE
set "DEFAULT_SAVE_PATH=!GAME_PATH!\SAVE"
set "SAVE_PATH="
set /p "SAVE_PATH=Save-file directory (default: !DEFAULT_SAVE_PATH!): "
if "!SAVE_PATH!"=="" set "SAVE_PATH=!DEFAULT_SAVE_PATH!"

rem ── 4. Build if not already built ────────────────────────────────────────
if not exist "!EXE_PATH!" (
    echo.
    echo [INFO] Compiled executable not found; building Release x86 ...
    dotnet build WITPAE_Theater_Staff.sln -c Release -p:Platform=x86 --nologo
    if errorlevel 1 (
        echo.
        echo [ERROR] Build failed. See output above for details.
        pause
        exit /b 1
    )
    echo [INFO] Build succeeded.
)

rem ── 5. Launch the application ─────────────────────────────────────────────
echo.
echo [INFO] Starting WITPAE Theater Staff ...
echo        Side      : !RUN_SIDE!
echo        Game dir  : !GAME_PATH!
echo        Save dir  : !SAVE_PATH!
echo.

"!EXE_PATH!" --side "!RUN_SIDE!" --game-path "!GAME_PATH!" --save-path "!SAVE_PATH!"
exit /b %errorlevel%

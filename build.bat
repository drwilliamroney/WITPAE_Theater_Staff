@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

rem ============================================================
rem  build.bat — WITPAE Theater Staff one-click build
rem
rem  Builds the solution as x86 ONLY (required to load the
rem  32-bit game DLLs in-process via P/Invoke).
rem
rem  Prompts for:
rem    Configuration  Debug | Release  (default: Release)
rem    Run tests?     y | n            (default: y)
rem
rem  Requirements:
rem    .NET 8 SDK — https://dotnet.microsoft.com/download
rem ============================================================

set "DEFAULT_CONFIG=Release"
set "X86_DOTNET=C:\Program Files (x86)\dotnet\dotnet.exe"

goto main

:ensure_runtime
if not exist "%X86_DOTNET%" goto install_runtime
"%X86_DOTNET%" --list-runtimes | findstr /R /C:"Microsoft.WindowsDesktop.App 8\.[0-9]" >nul 2>&1
if not errorlevel 1 goto :eof

:install_runtime
where winget >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] .NET 8 x86 Windows Desktop Runtime is required to run tests locally.
    echo         Install it with:
    echo         winget install --id Microsoft.DotNet.DesktopRuntime.8 --architecture x86
    echo.
    pause
    exit /b 1
)

echo.
echo [INFO] Installing missing .NET 8 x86 Windows Desktop Runtime...
winget install --id Microsoft.DotNet.DesktopRuntime.8 --architecture x86 --accept-package-agreements --accept-source-agreements --silent
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install .NET 8 x86 Windows Desktop Runtime.
    pause
    exit /b 1
)
goto :eof

:main

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

for /f "tokens=1" %%v in ('dotnet --version 2^>nul') do set "DOTNET_VER=%%v"
if "%DOTNET_VER:~0,1%" neq "8" (
    echo.
    echo [WARNING] .NET %DOTNET_VER% detected; .NET 8 is recommended.
    echo           The build may still succeed, but results are untested.
    echo.
)

rem ── 2. Prompt for configuration ──────────────────────────────────────────
echo.
set "BUILD_CONFIG="
set /p "BUILD_CONFIG=Build configuration [Debug/Release] (default: %DEFAULT_CONFIG%): "
if "!BUILD_CONFIG!"=="" set "BUILD_CONFIG=%DEFAULT_CONFIG%"
if /I "!BUILD_CONFIG!"=="debug"   set "BUILD_CONFIG=Debug"
if /I "!BUILD_CONFIG!"=="release" set "BUILD_CONFIG=Release"
if /I not "!BUILD_CONFIG!"=="Debug" if /I not "!BUILD_CONFIG!"=="Release" (
    echo   Invalid value "!BUILD_CONFIG!" — using default: %DEFAULT_CONFIG%
    set "BUILD_CONFIG=%DEFAULT_CONFIG%"
)

rem ── 3. Prompt: run tests? ─────────────────────────────────────────────────
set "RUN_TESTS="
set /p "RUN_TESTS=Run unit tests after build? [y/n] (default: y): "
if "!RUN_TESTS!"=="" set "RUN_TESTS=y"

rem ── 4. Restore ───────────────────────────────────────────────────────────
echo.
echo [INFO] Restoring NuGet packages...
dotnet restore WITPAE_Theater_Staff.sln --nologo
if errorlevel 1 (
    echo.
    echo [ERROR] NuGet restore failed. See output above.
    pause
    exit /b 1
)

rem ── 5. Build (x86 ONLY) ──────────────────────────────────────────────────
echo.
echo [INFO] Building  !BUILD_CONFIG!^|x86 ...
dotnet build WITPAE_Theater_Staff.sln ^
    -c "!BUILD_CONFIG!" ^
    -p:Platform=x86 ^
    --no-restore ^
    --nologo
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above for details.
    pause
    exit /b 1
)
echo.
echo [INFO] Build succeeded: !BUILD_CONFIG!^|x86

rem ── 6. Tests (optional) ──────────────────────────────────────────────────
if /I "!RUN_TESTS!"=="y" (
    call :ensure_runtime
    echo.
    echo [INFO] Running unit tests...
    dotnet test WITPAE_Theater_Staff.sln ^
        -c "!BUILD_CONFIG!" ^
        -p:Platform=x86 ^
        --no-build ^
        --nologo ^
        --logger "console;verbosity=normal"
    if errorlevel 1 (
        echo.
        echo [ERROR] One or more tests failed. See output above.
        pause
        exit /b 1
    )
    echo.
    echo [INFO] All tests passed.
)

rem ── 7. Done ──────────────────────────────────────────────────────────────
echo.
echo [INFO] Done.  Output: src\WitpaeTheaterStaff\bin\!BUILD_CONFIG!\net8.0-windows\x86\
echo.
pause
exit /b 0

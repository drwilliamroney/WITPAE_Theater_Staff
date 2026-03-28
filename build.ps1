<#
.SYNOPSIS
    One-click build script for WITPAE Theater Staff (x86 only).

.DESCRIPTION
    Restores NuGet packages, builds the solution as x86 (required for
    in-process loading of the 32-bit game DLLs via P/Invoke), and
    optionally runs all unit tests.

    Prompts for:
        Configuration   Debug | Release  (default: Release)
        Run tests?      y | n            (default: y)

.REQUIREMENTS
    .NET 8 SDK — https://dotnet.microsoft.com/download

.EXAMPLE
    # Interactive (prompts for configuration and test option)
    .\build.ps1

.EXAMPLE
    # Non-interactive: Release build + tests
    .\build.ps1 -Configuration Release -RunTests

.EXAMPLE
    # Debug build, skip tests
    .\build.ps1 -Configuration Debug -SkipTests
#>

[CmdletBinding()]
param(
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = '',

    [switch]$RunTests,
    [switch]$SkipTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Resolve script root ───────────────────────────────────────────────────────
Push-Location $PSScriptRoot

$x86Dotnet = 'C:\Program Files (x86)\dotnet\dotnet.exe'

function Write-Step  ([string]$msg) { Write-Host "`n[INFO] $msg"    -ForegroundColor Cyan  }
function Write-Ok    ([string]$msg) { Write-Host "[INFO] $msg"     -ForegroundColor Green }
function Write-Warn  ([string]$msg) { Write-Host "[WARN] $msg"     -ForegroundColor Yellow }
function Write-Fail  ([string]$msg) { Write-Host "`n[ERROR] $msg"  -ForegroundColor Red; throw $msg }

function Ensure-X86DesktopRuntime {
    if (Test-Path $x86Dotnet) {
        $runtimes = & $x86Dotnet --list-runtimes
        if ($runtimes -match 'Microsoft\.WindowsDesktop\.App 8\.') {
            return
        }
    }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Fail '.NET 8 x86 Windows Desktop Runtime is required. Install with: winget install --id Microsoft.DotNet.DesktopRuntime.8 --architecture x86'
    }

    Write-Step 'Installing missing .NET 8 x86 Windows Desktop Runtime...'
    & winget install --id Microsoft.DotNet.DesktopRuntime.8 --architecture x86 --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) { Write-Fail 'Failed to install .NET 8 x86 Windows Desktop Runtime.' }
}

try
{

# ── 1. Verify .NET SDK ────────────────────────────────────────────────────────
Write-Step 'Checking .NET SDK...'
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    Write-Fail '.NET SDK not found on PATH. Install from https://dotnet.microsoft.com/download'
}

$dotnetVer = (& dotnet --version 2>$null)
if ($dotnetVer -notmatch '^8\.') {
    Write-Warn ".NET $dotnetVer detected; .NET 8 is recommended."
} else {
    Write-Ok "  .NET $dotnetVer"
}

# ── 2. Prompt for configuration ───────────────────────────────────────────────
if ([string]::IsNullOrWhiteSpace($Configuration)) {
    $raw = Read-Host "`nBuild configuration [Debug/Release] (default: Release)"
    $Configuration = if ([string]::IsNullOrWhiteSpace($raw)) { 'Release' }
                     elseif ($raw -ieq 'debug')   { 'Debug' }
                     elseif ($raw -ieq 'release')  { 'Release' }
                     else {
                         Write-Warn "Unknown value '$raw'; using Release."
                         'Release'
                     }
}
Write-Ok "  Configuration: $Configuration|x86"

# ── 3. Prompt: run tests? ─────────────────────────────────────────────────────
$doTests = $RunTests.IsPresent
if (-not $doTests -and -not $SkipTests.IsPresent) {
    $raw = Read-Host "`nRun unit tests after build? [y/n] (default: y)"
    $doTests = ([string]::IsNullOrWhiteSpace($raw)) -or ($raw -imatch '^y')
}

# ── 4. Restore ────────────────────────────────────────────────────────────────
Write-Step 'Restoring NuGet packages...'
& dotnet restore WITPAE_Theater_Staff.sln --nologo
if ($LASTEXITCODE -ne 0) { Write-Fail 'NuGet restore failed.' }
Write-Ok '  Restore complete.'

# ── 5. Build (x86 ONLY) ───────────────────────────────────────────────────────
Write-Step "Building $Configuration|x86..."
& dotnet build WITPAE_Theater_Staff.sln `
    -c $Configuration `
    -p:Platform=x86 `
    --no-restore `
    --nologo
if ($LASTEXITCODE -ne 0) { Write-Fail 'Build failed.' }
Write-Ok "  Build succeeded: $Configuration|x86"

# ── 6. Tests (optional) ───────────────────────────────────────────────────────
if ($doTests) {
    Ensure-X86DesktopRuntime
    Write-Step 'Running unit tests...'
    & dotnet test WITPAE_Theater_Staff.sln `
        -c $Configuration `
        -p:Platform=x86 `
        --no-build `
        --nologo `
        --logger "console;verbosity=normal"
    if ($LASTEXITCODE -ne 0) { Write-Fail 'One or more tests failed.' }
    Write-Ok '  All tests passed.'
}

# ── 7. Done ───────────────────────────────────────────────────────────────────
$outDir = Join-Path $PSScriptRoot "src\WitpaeTheaterStaff\bin\$Configuration\net8.0-windows\x86\"
Write-Host ''
Write-Ok "Done.  Output: $outDir"

}
finally
{
    Pop-Location
}

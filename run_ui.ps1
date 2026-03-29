<#
.SYNOPSIS
    Launch WITPAE Theater Staff (PyQt5) with Python x86 3.13+ checks.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot

function Test-PythonX86 {
    param([Parameter(Mandatory = $true)][string]$PythonExe)

    if (-not (Test-Path $PythonExe)) { return $false }

    & $PythonExe -c "import struct,sys; raise SystemExit(0 if (sys.version_info[:2] == (3, 13) and struct.calcsize('P') * 8 == 32) else 1)" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Resolve-Python {
    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (Test-PythonX86 -PythonExe $venvPython) {
        return $venvPython
    }

    $candidates = @(
        @{ Launcher = 'py'; Args = @('-3.13-32', '-c', 'import sys; print(sys.executable)') },
        @{ Launcher = 'python'; Args = @('-c', 'import sys; print(sys.executable)') }
    )

    foreach ($candidate in $candidates) {
        try {
            $exe = & $candidate.Launcher @($candidate.Args) 2>$null
            if ($LASTEXITCODE -eq 0 -and [string]::IsNullOrWhiteSpace($exe) -eq $false) {
                $resolved = $exe.Trim()
                if (Test-PythonX86 -PythonExe $resolved) {
                    return $resolved
                }
            }
        }
        catch {
        }
    }

    throw @"
Python x86 3.13 was not found.

Install instructions:
    1) Download Python 3.13 Windows installer (32-bit):
     https://www.python.org/downloads/windows/
  2) Run installer and enable 'Add python.exe to PATH'.
  3) Re-run this script.

Verification command:
  py -3.13-32 -c "import struct,sys; print(sys.version); print(struct.calcsize('P')*8)"
"@
}

function Test-GameDlls {
    param([Parameter(Mandatory = $true)][string]$GamePath)

    $dlls = @('pwsdll.dll', 'pwsdll7.dll')
    $missing = $false
    foreach ($dll in $dlls) {
        $fullPath = Join-Path $GamePath $dll
        if (Test-Path $fullPath) {
            Write-Host "[INFO] $dll detected"
        }
        else {
            Write-Host "[ERROR] $dll NOT detected"
            $missing = $true
        }
    }

    if ($missing) {
        throw "Required game DLLs were not found in '$GamePath'."
    }
}

function Show-PythonInfo {
    param([Parameter(Mandatory = $true)][string]$PythonExe)

    Write-Host "[INFO] Python executable: $PythonExe"
    & $PythonExe -c "import struct,sys; print('[INFO] Python version   :', sys.version.split()[0]); print('[INFO] Python architecture:', str(struct.calcsize('P')*8) + '-bit')" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[WARN] Failed to query Python runtime details.'
    }
}

function Ensure-Venv {
    param([Parameter(Mandatory = $true)][string]$PythonExe)

    $venvDir = Join-Path $PSScriptRoot '.venv'
    $venvPython = Join-Path $venvDir 'Scripts\python.exe'

    Write-Host '[INFO] Preparing Python environment...'

    if ((Test-Path $venvPython) -and (-not (Test-PythonX86 -PythonExe $venvPython))) {
        Write-Host '[WARN] Existing .venv is not Python 3.13 x86. Rebuilding .venv ...'
        Remove-Item -Path $venvDir -Recurse -Force
    }

    if (-not (Test-Path $venvPython)) {
        Write-Host '[INFO] Creating virtual environment at .venv ...'
        & $PythonExe -m venv $venvDir
        if ($LASTEXITCODE -ne 0) { throw 'Failed to create .venv.' }
    }

    Write-Host '[INFO] Installing dependencies...'
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'Failed to upgrade pip.' }

    & $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install dependencies.' }

    & $venvPython -c "import PyQt5, PIL, rich" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'Python dependencies are not importable. WITPAE Theater Staff currently requires Python 3.13 x86 for PyQt5. Remove .venv and re-run with Python 3.13-32.'
    }

    return $venvPython
}

try {
    $defaultSide = 'allies'
    $defaultGamePath = 'C:\Matrix Games\War in the Pacific Admiral''s Edition'

    $pythonExe = Resolve-Python

    $side = Read-Host "Run as [allies/japan] (default: $defaultSide)"
    if ([string]::IsNullOrWhiteSpace($side)) { $side = $defaultSide }
    if ($side -notin @('allies', 'japan')) {
        Write-Host "[WARN] Invalid side '$side' - using $defaultSide"
        $side = $defaultSide
    }

    $gamePath = Read-Host "Game / save directory path (default: $defaultGamePath)"
    if ([string]::IsNullOrWhiteSpace($gamePath)) { $gamePath = $defaultGamePath }
    $savePath = Join-Path $gamePath 'SAVE'

    Test-GameDlls -GamePath $gamePath
    Show-PythonInfo -PythonExe $pythonExe
    $venvPython = Ensure-Venv -PythonExe $pythonExe

    Write-Host "[INFO] Starting WITPAE Theater Staff ..."
    Write-Host "       Side      : $side"
    Write-Host "       Game dir  : $gamePath"
    Write-Host "       Save dir  : $savePath"
    Write-Host "       Python    : $venvPython"

    & $venvPython -m app.main --side $side --game-path $gamePath --save-path $savePath
    exit $LASTEXITCODE
}
catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    if ($Host.Name -eq 'ConsoleHost') {
        [void](Read-Host 'Press Enter to close')
    }
    exit 1
}
finally {
    Pop-Location
}

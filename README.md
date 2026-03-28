# WITPAE Theater Staff

> **AI-First Research Notice** — This repository is **100% built by GitHub
> Copilot** and constitutes a scientific experiment in the emerging *AI-First*
> working pattern for software developers, conducted by **William N. Roney,
> ScD**.  No human-authored source code is written; all design decisions,
> implementations, refactors, and repository operations are performed through
> natural-language instruction to the Copilot agent.

---

## What this is

**WITPAE Theater Staff** is a single, fully-integrated Windows 11+ desktop
application for *War in the Pacific: Admiral's Edition* game management.

The game is a turn-based, hex-map grand strategy simulation of the Pacific
Theater of World War 2.  The application provides augmented information about
the current game-turn state: a hardware-rendered map overlaid with unit
positions, task-force movements, base supply health, air-group missions,
ground-unit dispositions, and threat heat-maps — the digital equivalent of a
paper map with acetate and dry-marker overlays.

---

## Technology decision

### The core constraint: 32-bit DLLs

The game ships two 32-bit Windows DLLs (`pwsdll.dll` and `pwsdll7.dll`) that
expose a C interface for reading game data from save files.  Any runtime that
wishes to call these DLLs **in-process** must itself run as a 32-bit process.
This single requirement drove the entire technology selection.

### Options considered

| Option | 32-bit DLL access | Notes |
|---|---|---|
| **Python (32-bit) + tkinter** | Yes, via `ctypes` | Existing code reusable; tkinter is dated and CPU-only |
| **C# WPF compiled `x86`** | Yes, via P/Invoke | Modern WPF Canvas; hardware-accelerated; VS 2022 designer |
| **C# WPF compiled `AnyCPU`/`x64`** | No | `BadImageFormatException` when loading 32-bit DLLs |
| **C# WinUI 3 compiled `x86`** | Yes, via P/Invoke | Windows 11 Fluent; more complex project setup |
| **C++/Win32 compiled `x86`** | Yes, native | Original LegacyDemoApp approach; higher effort, no managed runtime |
| **Hybrid 64-bit frontend + 32-bit subprocess** | Indirect | Recreates the old 2-process IPC complexity |

### Detailed comparison: Python/tkinter vs C# WPF

| Criterion | Python/tkinter | **C# WPF (x86) — chosen** |
|---|---|---|
| Modern UI | No — tkinter looks dated | Yes — WPF/Fluent controls |
| Hardware-accelerated map | No — CPU-only Canvas | Yes — WPF Canvas uses DirectX |
| 32-bit DLL access | Yes — but requires unusual 32-bit Python install | Yes — standard .NET x86 target |
| Overlay model fit | Limited | Excellent — WPF Canvas + named child elements |
| Type safety | Partial (type hints) | Full static typing |
| IDE tooling | Basic | VS 2022 designer, hot reload, IntelliSense |
| Deployment | Requires 32-bit Python venv | Self-contained `.exe`, no runtime install |
| CI/CD | `pytest` on Linux (cross-platform) | `dotnet test` on `windows-latest` (matches target OS) |
| Test framework | pytest | xUnit — integrated with VS Test Explorer |

**Decision: C# WPF, compiled as `x86` only, targeting `.NET 8`.**

A single, self-contained `.exe` that loads 32-bit game DLLs via P/Invoke,
renders the map on a hardware-accelerated WPF Canvas, and ships without
requiring any external runtime installation.

---

## Architecture

```
WITPAE_Theater_Staff.sln
run_ui.bat                          <- interactive launcher with defaults
src/
  WitpaeTheaterStaff/
    WitpaeTheaterStaff.csproj       <- net8.0-windows, PlatformTarget=x86
    App.xaml / App.xaml.cs         <- entry-point; parses CLI args / env vars
    MainWindow.xaml / .cs          <- root window: toolbar, map, detail panel
    DllInterface/
      GameEnums.cs                 <- C# enums (RecType, Side, Nationality, ...)
      PwsDllStructs.cs             <- [StructLayout(Sequential)] P/Invoke structs
      PwsDll.cs                    <- NativeLibrary.Load; typed record accessors
    Data/
      Models/                      <- pure C# records (no WPF dependencies)
        TurnInfo.cs
        ShipRecord.cs
        AirGroupRecord.cs
        GroundUnitRecord.cs
        TaskForceRecord.cs
        BaseRecord.cs
        GameState.cs
      GameDataScraper.cs           <- DLL calls -> GameState; JSON fallback
      TurnWatcher.cs               <- FileSystemWatcher; NewTurnDetected event
    UI/
      CoordinateTransform.cs       <- hex <-> pixel math (unit-testable)
      MapAssembly.cs               <- stitches WPEN??.bmp tiles
      OverlayBuilder.cs            <- WPF shapes per overlay layer
      HexTooltip.cs                <- ToolTip content factory
      DetailPanel.xaml / .cs      <- TreeView detail panel (right side)
    Config/
      AppSettings.cs               <- System.Text.Json settings
      SettingsWindow.xaml / .cs   <- modal settings dialog
tests/
  WitpaeTheaterStaff.Tests/
    WitpaeTheaterStaff.Tests.csproj  <- net8.0-windows, x86, xUnit 2.9+
    CoordinateTransformTests.cs
    GameDataModelsTests.cs
    GameEnumsTests.cs
```

### Overlay layer tags

| Tag | Content |
|---|---|
| `overlay_region` | Theater-region polygons |
| `overlay_tf` | Task-force movement arrows |
| `overlay_ship` | Individual ship dots |
| `overlay_base` | Base circles (colour = supply health) |
| `overlay_air` | Air-group dots + search/ASW arcs |
| `overlay_land` | Ground-unit markers |
| `overlay_threat` | Threat-hex heat-map cells |

### Coordinate system

The game uses a 232 x 205 hex grid (1-indexed).

```
stepX = canvasWidth  / (232 - 1)
stepY = canvasHeight / (205 - 1)
hexCenter = ((hexX - 1) * stepX + stepX/2,
             (hexY - 1) * stepY + stepY/2)
```

---

## Building and running

### Prerequisites

- Windows 11 (or Windows 10 21H2+)
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8)
- *War in the Pacific: Admiral's Edition* installed
  (default: `C:\Matrix Games\War in the Pacific Admiral's Edition`)

### Quick start

```bat
run_ui.bat
```

The script will:
1. Verify .NET 8 SDK is on `PATH`.
2. Prompt for **side** (`allies`/`japan`; default: `allies`).
3. Prompt for **game directory** (default: `C:\Matrix Games\War in the Pacific Admiral's Edition`).
4. Prompt for **save-file directory** (default: `<game dir>\SAVE`).
5. Build `Release|x86` if not already present.
6. Launch `WitpaeTheaterStaff.exe` with the selected parameters.

### Manual build

```bat
dotnet build WITPAE_Theater_Staff.sln -c Release -p:Platform=x86
```

### Running tests

```bat
dotnet test WITPAE_Theater_Staff.sln -c Release -p:Platform=x86
```

---

## CI/CD

Every push and pull-request to `main` triggers `.github/workflows/ci.yml`:

1. Restore NuGet packages.
2. Build `Release|x86`.
3. Run all unit tests with `dotnet test`.
4. Upload `.trx` test result files as a workflow artifact.

Tests requiring actual game DLLs are marked
`[Fact(Skip = "Requires game DLLs")]` so CI passes without a game install.

---

## Legacy history

| Repo | Language | Role | Status |
|---|---|---|---|
| [LegacyDemoApp](https://github.com/drwilliamroney/LegacyDemoApp) | C++ (x86) | First-generation DLL datascraper | Superseded |
| [pywitpaescraper](https://github.com/drwilliamroney/pywitpaescraper) | Python 32-bit | ctypes DLL wrapper + JSON export | Superseded |
| [pywitpaeui](https://github.com/drwilliamroney/pywitpaeui) | Python 64-bit / FastAPI | Browser-based UI | Superseded |

The two-process architecture introduced 32/64-bit IPC complexity and
browser-based image-overlay latency. This application eliminates both by
running a single 32-bit WPF process that owns the full stack from DLL
extraction to hardware-rendered map display.

---

## AI-First experiment notes

Constraints:
- **No human-authored source code** — every `.cs`, `.xaml`, `.bat`, `.yml`,
  and `.md` file is produced by GitHub Copilot.
- **Human role** — architectural direction, acceptance testing, and
  natural-language feedback.
- **AI role** — design, implementation, refactoring, documentation, and
  repository operations.

The experiment tests whether Copilot can build and maintain a non-trivial,
Windows-native desktop application end-to-end, including correct low-level
binary interop with undocumented game data structures, hardware-accelerated
graphics, and a fully automated CI/CD pipeline.

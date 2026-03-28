# WITPAE Theater Staff — GitHub Copilot Instructions

## Project purpose

**WITPAE Theater Staff** is a single, fully-integrated Windows desktop
application for *War in the Pacific: Admiral's Edition* game management.
It is simultaneously a functional tool and a scientific experiment in
**AI-First software development** — all design decisions and code are
produced by GitHub Copilot with natural-language direction from the human
researcher.  No human-authored source code is written.

---

## Technology stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | C# 12 | Type-safe, modern, excellent tooling |
| UI framework | WPF (.NET 8, `net8.0-windows`) | Native hardware-accelerated Canvas; perfect overlay model |
| Platform target | **x86 ONLY** | Game DLLs (`pwsdll.dll`, `pwsdll7.dll`) are 32-bit; P/Invoke requires matching bitness |
| DLL interop | `System.Runtime.InteropServices` (P/Invoke via `NativeLibrary`) | Direct in-process call — no subprocess, no IPC |
| Settings persistence | `System.Text.Json` | Built-in, no extra dependencies |
| Unit testing | xUnit 2.9+ | .NET-ecosystem standard; integrates with VS Test Explorer and `dotnet test` |
| CI/CD | GitHub Actions (`windows-latest`) | Builds x86 Release, runs all tests on every push/PR |

> **Why not Python/tkinter?**  See `README.md` § *Technology decision* for
> the full trade-off analysis.

---

## x86-only constraint — never violate this

- The Visual Studio solution exposes **only `Debug|x86` and `Release|x86`**
  configurations.  `AnyCPU` and `x64` are deliberately absent.
- The main project's `.csproj` contains `<PlatformTarget>x86</PlatformTarget>`
  and `<Platforms>x86</Platforms>`.
- The tests project also targets x86 so tests run with the same bitness as
  the application.
- **Never add an `AnyCPU` or `x64` configuration.**  Loading a 32-bit DLL
  from a 64-bit process will throw a `BadImageFormatException` at runtime.

---

## Repository layout

```
WITPAE_Theater_Staff.sln
run_ui.bat                              <- launcher with interactive prompts
src/
  WitpaeTheaterStaff/
    WitpaeTheaterStaff.csproj           <- net8.0-windows, x86 ONLY
    App.xaml / App.xaml.cs             <- entry point; reads CLI args / env vars
    MainWindow.xaml / .cs              <- toolbar + map canvas + detail panel
    DllInterface/
      GameEnums.cs                     <- C# enums mirroring pwsdll.py IntEnums
      PwsDllStructs.cs                 <- [StructLayout(Sequential)] mirrors of ctypes structs
      PwsDll.cs                        <- NativeLibrary.Load wrapper; typed accessors
    Data/
      Models/                          <- pure C# record types (no WPF dependencies)
        TurnInfo.cs
        ShipRecord.cs
        AirGroupRecord.cs
        GroundUnitRecord.cs
        TaskForceRecord.cs
        BaseRecord.cs
        GameState.cs
      GameDataScraper.cs               <- orchestrates DLL calls -> populates GameState
      TurnWatcher.cs                   <- FileSystemWatcher; fires NewTurnDetected event
    UI/
      CoordinateTransform.cs           <- hex <-> pixel math (no WPF refs, unit-testable)
      MapAssembly.cs                   <- stitches WPEN??.bmp tiles; placeholder fallback
      OverlayBuilder.cs                <- builds WPF shapes for each overlay layer
      HexTooltip.cs                    <- ToolTip content factory
      DetailPanel.xaml / .cs          <- right-side TreeView detail panel
    Config/
      AppSettings.cs                   <- JSON-persisted settings model + loader/saver
      SettingsWindow.xaml / .cs       <- modal settings dialog
tests/
  WitpaeTheaterStaff.Tests/
    WitpaeTheaterStaff.Tests.csproj    <- net8.0-windows, x86, xUnit
    CoordinateTransformTests.cs
    GameDataModelsTests.cs
    GameEnumsTests.cs
```

---

## Coding conventions

### General
- **C# 12** features are encouraged: primary constructors, collection
  expressions, `required` properties, pattern matching.
- All `public` and `internal` types and members must have **XML doc comments**
  (`/// <summary>`).
- Use `sealed` on leaf classes unless inheritance is intentional.
- Prefer `record` or `record struct` for immutable data transfer objects.
- Use `ArgumentNullException.ThrowIfNull` and
  `ArgumentException.ThrowIfNullOrWhiteSpace` for guard clauses.

### Naming
- Types, methods, properties: `PascalCase`
- Parameters, local variables: `camelCase`
- Private fields: `_camelCase`
- Constants: `PascalCase` (not `ALL_CAPS`)

### Error handling
- DLL errors must propagate as `DllNotAvailableException` (defined in
  `DllInterface/PwsDll.cs`), never swallowed silently.
- `GameDataScraper` falls back to JSON exports when `DllNotAvailableException`
  is caught, so the UI loads without a game installation.
- Log via `System.Diagnostics.Trace` or `ILogger`.

### WPF patterns
- Root window uses `DockPanel`.  Inner layouts use `Grid`.
- Canvas overlay items are tagged with the overlay-layer string constant
  (e.g. `"overlay_tf"`).  Show/hide by filtering `Canvas.Children` on `Tag`.
- Bind simple view-state (labels, status counts) in code-behind.
  MVVM data binding is **not required** for this application.

### Interop / P/Invoke
- Load DLLs with `NativeLibrary.Load(absolutePath)` — never rely on PATH.
- All P/Invoke structs use `[StructLayout(LayoutKind.Sequential)]` **without**
  an explicit `Pack` value — natural alignment matches Python ctypes defaults.
- Decode C-string fields with
  `Encoding.Latin1.GetString(bytes).TrimEnd('\0').Trim()`.
- Iterate records with pointer arithmetic:
  `Marshal.PtrToStructure<T>(ptr + i * Marshal.SizeOf<T>())`.
  Stop iteration when the name/key field is empty.

### Testing
- **Every non-WPF class must have at least one unit test.**
- Tests live in `tests/WitpaeTheaterStaff.Tests/`.
- Tests that require actual game DLLs are skipped on CI with
  `[Fact(Skip = "Requires game DLLs")]`.
- Do NOT test WPF `Window`/`Control` subclasses directly; test the underlying
  logic classes (`CoordinateTransform`, `AppSettings`, model helpers).
- Aim for 100% branch coverage of `CoordinateTransform.cs` and all
  `Data/Models/*.cs`.

---

## CI/CD process

`.github/workflows/ci.yml` runs on every push and pull-request to `main`:

1. **Restore** — `dotnet restore`
2. **Build** — `dotnet build -c Release -p:Platform=x86 --no-restore`
3. **Test** — `dotnet test -c Release -p:Platform=x86 --no-build --logger trx`
4. **Upload** test results as a workflow artifact

All steps run on `windows-latest` (required for WPF / Windows target).
The build **must pass** before a PR can be merged.

---

## Legacy context

| Repo | Language | Role | Status |
|---|---|---|---|
| [LegacyDemoApp](https://github.com/drwilliamroney/LegacyDemoApp) | C++ (x86) | DLL datascraper | Superseded |
| [pywitpaescraper](https://github.com/drwilliamroney/pywitpaescraper) | Python 32-bit | DLL wrapper + JSON export | Superseded |
| [pywitpaeui](https://github.com/drwilliamroney/pywitpaeui) | Python 64-bit / FastAPI | Browser-based UI | Superseded |

The ctypes struct definitions in `pywitpaescraper/pwsdll.py` are the
authoritative reference for the game binary record layout.  All
`[StructLayout]` structs in `PwsDllStructs.cs` must be cross-checked against
that file.

# Technology Comparison — WITPAE Theater Staff

## The Hard Constraint

The application must call functions exported by a **third-party 32-bit (x86) DLL**
that uses **32-bit (4-byte) struct alignment**.  This single constraint drives most
of the analysis below because it rules out mixed-bitness processes:

> A 64-bit host process **cannot** directly call a 32-bit DLL in the same address
> space.  The host process (Python interpreter, .NET runtime, C++ EXE, etc.) must
> itself be compiled and launched as a 32-bit (x86) process.

Every option below satisfies this constraint when configured correctly; the
comparison focuses on *how hard it is to configure correctly* and what the
trade-offs are once it is.

---

## Options Considered

| # | Stack | IDE / Toolchain | Language |
|---|-------|-----------------|----------|
| 1 | **32-bit Python 3 + tkinter** *(current)* | VS Code, PyCharm CE, Notepad++ | Python |
| 2 | **.NET Framework 4.x — Windows Forms** | Visual Studio Community 2022 | C# or VB.NET |
| 3 | **.NET Framework 4.x — WPF** | Visual Studio Community 2022 | C# or VB.NET |
| 4 | **Native C++ — Win32 / MFC** | Visual Studio Community 2022 | C++ |
| 5 | **C++/CLI (mixed managed + native)** | Visual Studio Community 2022 | C++/CLI |
| 6 | **.NET 6/8 + Windows Forms or WPF** | Visual Studio Community 2022 | C# |

---

## Option 1 — 32-bit Python 3 + tkinter *(current choice)*

### How the DLL is called

Python's standard-library `ctypes` module loads the DLL at runtime and marshals
calls in-process.  Struct alignment is controlled by `_pack_`:

```python
import ctypes

class UnitRecord(ctypes.Structure):
    _pack_ = 4          # match the DLL's 32-bit alignment
    _fields_ = [
        ("unit_id",   ctypes.c_uint32),
        ("hex_col",   ctypes.c_int16),
        ("hex_row",   ctypes.c_int16),
        ("strength",  ctypes.c_float),
    ]

dll = ctypes.CDLL("witpae_data.dll")
dll.GetUnit.restype  = ctypes.c_int
dll.GetUnit.argtypes = [ctypes.c_uint32, ctypes.POINTER(UnitRecord)]
```

Alternatively, `cffi` provides a slightly safer, more C-like interface and can
parse C header fragments directly.

### 32-bit requirement

The Python **interpreter** binary must be the x86 (32-bit) build.  `run_gui.bat`
already verifies this using `struct.calcsize('P') * 8 == 32` before launching.

### Pros

- **Zero ramp-up** — scaffold is already in place and working.
- **No compile step** — edit a `.py` file, re-run, see the result immediately.
  Ideal for a rapidly evolving helper tool.
- **Rich ecosystem** — `pandas` for data manipulation, `matplotlib` for charts,
  `Pillow` for map image handling, all pip-installable with zero build overhead.
- **`ctypes._pack_`** directly mirrors `#pragma pack(4)` and is well-documented.
  Writing a unit test that asserts `ctypes.sizeof(UnitRecord) == <expected>` catches
  layout bugs before they reach the DLL call.
- **Free, cross-IDE** — works with VS Code (free), PyCharm Community (free), or
  any text editor.  No licence management.
- **Simple deployment** — PyInstaller (32-bit build) bundles everything into a
  single `.exe` or folder that end-users can run without installing Python.

### Cons

- **Runtime type safety** — struct field types are strings/ctypes objects, not
  verified by a compiler.  A typo in `_fields_` only fails at runtime.
- **32-bit Python is non-default** — Python.org now prominently offers 64-bit
  installers; users must consciously choose the 32-bit download.
- **tkinter aesthetics** — the default tkinter theme looks dated compared to
  Windows Forms or WPF; custom theming requires `ttkthemes` or manual work.
- **Performance** — Python adds overhead per call.  For a UI tool this is
  irrelevant, but tight loops over thousands of DLL calls would be slower.
- **GIL** — background DLL calls must release the GIL or be run in a thread with
  `ctypes.CDLL("...", use_last_error=True)` idiom; requires care.

### Verdict

**Best fit for this project in its current stage.**  The application is a staff
tool, not a game engine.  Rapid iteration, a wide data-processing ecosystem, and
zero build infrastructure outweigh the type-safety gap that can be closed with
assertions and unit tests.

---

## Option 2 — C# + .NET Framework 4.x + Windows Forms

### How the DLL is called

P/Invoke (Platform Invocation Services) with explicit struct layout attributes:

```csharp
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential, Pack = 4)]
public struct UnitRecord
{
    public uint   UnitId;
    public short  HexCol;
    public short  HexRow;
    public float  Strength;
}

static class WitpaeDll
{
    [DllImport("witpae_data.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern int GetUnit(uint unitId, out UnitRecord record);
}
```

### 32-bit requirement

In Visual Studio: **Project → Properties → Build → Platform target = x86**.
This is a single checkbox; the resulting EXE is a true 32-bit process.

### Pros

- **Compile-time type checking** — `Pack = 4` and field types are validated by the
  C# compiler and the Roslyn analyser.  Struct-size mismatches surface before the
  program runs.
- **Visual Studio Designer** — drag-and-drop Windows Forms layout editor speeds up
  building data-entry forms and dialogs.
- **IntelliSense + debugger** — industry-leading IDE experience with breakpoints,
  watch windows, and memory inspection.
- **Strong typing throughout** — catches far more errors before runtime than Python.
- **.NET Framework 4.x is mature** — x86 target is fully supported, well-tested,
  and ships with every modern Windows installation.
- **Free** — Visual Studio Community is free for individual developers, open-source
  projects, students, and small teams (≤ 5 users in non-enterprise settings).
- **NuGet** — large package ecosystem (charting, map rendering, data grids).

### Cons

- **Build step required** — every change requires a compile before testing.
  For a rapidly evolving UI tool this slows iteration.
- **More boilerplate** — C# requires explicit type declarations, namespaces, and
  project files.  A 50-line Python function may become 150 lines of C#.
- **Windows-only deployment** — fine here, but worth noting.
- **.NET Framework is legacy** — Microsoft's investment is in .NET 6+; Framework
  4.x is maintained but receives only security patches.
- **Windows Forms aesthetics** — still more polished than default tkinter but less
  flexible than WPF for custom rendering (e.g., a hex-grid canvas).

### Verdict

**Strong alternative, especially if the team is already C#-fluent.**  If the DLL
integration is complex (dozens of functions, large structs, performance-critical
paths), the compile-time safety of P/Invoke with explicit `Pack = 4` attributes
makes C# + Windows Forms a compelling migration target.

---

## Option 3 — C# + .NET Framework 4.x + WPF

### How the DLL is called

Identical to Option 2 (P/Invoke + `[StructLayout]`).

### Additional notes

WPF uses a **retained-mode GPU-accelerated renderer** (DirectX under the hood) and
a declarative XAML layout language.  This makes it significantly better than
Windows Forms for a custom hex-grid canvas — smooth zoom, pan, and per-hex
highlighting are straightforward via `DrawingVisual` or a `Canvas` with `Path`
elements.

### Pros

- All of Option 2's pros, plus:
- **Custom rendering** — `DrawingContext`, `WriteableBitmap`, or `SharpDX`/`SkiaSharp`
  on top of WPF give pixel-level control of the map display.
- **Modern look** — XAML styles and control templates produce polished, themeable UIs.
- **MVVM pattern** — data-binding separates UI from game-data logic cleanly.
- **`Canvas` element** — closely parallels the tkinter `Canvas` already planned,
  easing a hypothetical migration.

### Cons

- **Steeper learning curve** — XAML + data binding + MVVM add conceptual overhead
  for developers new to WPF.
- **Slower prototyping** — no drag-and-drop designer as mature as Windows Forms.
- All of Option 2's cons.

### Verdict

**Best long-term GUI choice if the project grows into a rich map-rendering tool.**
For the current staff-tool scope, the extra complexity is not yet warranted.

---

## Option 4 — Native C++ (Win32 API or MFC) — Visual Studio Community

### How the DLL is called

Direct linkage — link against the import library (`.lib`) or use `LoadLibrary` /
`GetProcAddress` at runtime.  Struct layout is controlled with `#pragma pack`:

```cpp
#pragma pack(push, 4)
struct UnitRecord {
    uint32_t unit_id;
    int16_t  hex_col;
    int16_t  hex_row;
    float    strength;
};
#pragma pack(pop)

extern "C" int GetUnit(uint32_t unit_id, UnitRecord* record);
```

If the DLL ships a header file, `#include` it directly — no re-declaration needed
and layout is guaranteed to match.

### 32-bit requirement

Set solution platform to **Win32** (not x64) in Configuration Manager.

### Pros

- **Zero interop overhead** — the DLL's functions are called as native function
  pointers; there is no marshalling layer.
- **Perfect alignment fidelity** — if the DLL ships headers, `#include` guarantees
  identical layout; `#pragma pack` mirrors the DLL's compilation settings exactly.
- **Compile-time errors** for every type mismatch.
- **Maximum performance** — relevant if the tool eventually processes large datasets
  from the DLL (thousands of units, supply lines, etc.).

### Cons

- **Highest development complexity** — Win32 message loops, MFC resource files,
  and manual memory management (even with smart pointers) are significantly more
  verbose than Python or C#.
- **MFC is dated** — the MFC widget set looks like a Windows 95 application unless
  heavily themed.
- **Slowest iteration** — recompile, relink, and restart for every change.
- **No modern alternative GUI** — Win32 with MFC has no equivalent to WPF's XAML
  or Python's ecosystem of hex-grid libraries.
- **Overkill** — for a staff tool that primarily reads data, displays it, and
  provides a planning overlay, native C++ adds complexity with marginal benefit.

### Verdict

**Not recommended** for this project.  The performance advantage is unnecessary
for a UI-driven helper tool, and the development velocity penalty is severe.
Reserve C++ for any future performance-critical computation kernel, potentially
as a separate helper DLL called from Python.

---

## Option 5 — C++/CLI (Mixed Managed + Native)

C++/CLI is a Microsoft extension of C++ that compiles to .NET IL but can directly
`#include` and link native C++ code in the same project.

### How the DLL is called

```cpp
// WrapperLib.h (C++/CLI ref class)
#include "witpae_data.h"   // native DLL header — alignment already correct

public ref class WitpaeBridge
{
public:
    static int GetUnit(unsigned int id, UnitRecord% record)
    {
        return ::GetUnit(id, &record);  // direct native call
    }
};
```

The C++/CLI wrapper DLL can then be consumed from C# or VB.NET with normal managed
references — no P/Invoke needed.

### Pros

- Solves the alignment problem at the C++ layer, freeing C# from `[StructLayout]`.
- Useful when the DLL ships complex C++ headers (vtables, templates) that P/Invoke
  cannot express.

### Cons

- Adds a second project and a second language to the solution.
- Only necessary when P/Invoke is insufficient (rare for a C-style DLL).
- Compilation complexity increases significantly.

### Verdict

**Niche option.**  Only consider if the DLL exports C++ classes or complex types
that resist P/Invoke marshalling.

---

## Option 6 — .NET 6 / 8 + Windows Forms or WPF

.NET 6+ is Microsoft's current cross-platform runtime.  However:

- **x86 (32-bit) support is second-class** — `win-x86` RID exists but is not
  tested or supported as broadly as `win-x64`.
- Windows Forms and WPF are Windows-only even in .NET 6+ (via
  `<UseWindowsForms>true</UseWindowsForms>`), which is acceptable here, but
- The **primary motivation for .NET 6+** — cross-platform and modern async
  patterns — are irrelevant to this Windows-only helper tool.
- P/Invoke syntax is identical to .NET Framework, so there is no interop advantage.

### Verdict

**No advantage over .NET Framework 4.x for this use case.**  Stick with Framework
4.x if choosing the C# path, as its x86 support is more mature and it ships with
Windows out of the box.

---

## Head-to-Head Summary

| Criterion | Python + ctypes | C# + WinForms (.NET Fx) | C# + WPF (.NET Fx) | Native C++ |
|-----------|:-:|:-:|:-:|:-:|
| **32-bit DLL interop** | ✅ (`_pack_`) | ✅ (`Pack=4`) | ✅ (`Pack=4`) | ✅ (`#pragma pack`) |
| **Alignment safety** | ⚠️ runtime | ✅ compile-time | ✅ compile-time | ✅ compile-time + headers |
| **Development speed** | ✅ fastest | 🔶 medium | 🔶 medium | ❌ slowest |
| **GUI quality** | ⚠️ dated | 🔶 good | ✅ excellent | ⚠️ dated |
| **Hex-grid rendering** | ✅ Canvas | ⚠️ custom paint | ✅ DrawingVisual | ⚠️ GDI/GDI+ |
| **No build step** | ✅ | ❌ | ❌ | ❌ |
| **Ecosystem (data/charts)** | ✅ pip | 🔶 NuGet | 🔶 NuGet | ❌ manual |
| **IDE cost** | ✅ free | ✅ free | ✅ free | ✅ free |
| **Deployment complexity** | 🔶 PyInstaller | 🔶 ClickOnce/installer | 🔶 ClickOnce/installer | ✅ xcopy |
| **Learning curve** | ✅ low | 🔶 medium | 🔶 medium–high | ❌ high |

✅ = advantage  🔶 = neutral / acceptable  ⚠️ = minor concern  ❌ = disadvantage

---

## Recommendation

### Stay with 32-bit Python 3 + tkinter for now

For the current scope — a **staff assistance and planning tool** for a single
player or small group — Python is the right choice:

1. **Already running** — no new toolchain to install or learn.
2. **Fastest iteration** — change a Python file, rerun, see the result.
3. **`ctypes` + `_pack_ = 4`** handles the alignment constraint cleanly; unit
   tests on `ctypes.sizeof` / `ctypes.offsetof` catch layout errors cheaply.
4. **Ecosystem** — `pandas`, `Pillow`, `matplotlib`, and hex-grid libraries are
   one `pip install` away.

### Migrate to C# + WPF (.NET Framework 4.x) if/when

- The team expands and compile-time type safety becomes more important than
  iteration speed.
- The hex-map display needs GPU-accelerated custom rendering (zoom, pan, layers).
- The DLL interface grows to dozens of functions with complex struct hierarchies.
- Packaging a polished end-user installer (rather than a dev-oriented `.bat`
  launcher) is required.

### DLL alignment in practice — both paths

Regardless of the chosen language, the following practice must be followed when
binding to the DLL:

| Language | Alignment directive | Size verification |
|----------|--------------------|--------------------|
| Python   | `Structure._pack_ = 4` | `assert ctypes.sizeof(S) == expected` |
| C#       | `[StructLayout(LayoutKind.Sequential, Pack = 4)]` | `Debug.Assert(Marshal.SizeOf<S>() == expected)` |
| C++      | `#pragma pack(push, 4)` / `#pragma pack(pop)` | `static_assert(sizeof(S) == expected)` |

Always cross-reference these sizes against the DLL's own documentation or header
files.  A struct-size unit test is the single most effective safeguard against
silent data corruption in DLL calls.

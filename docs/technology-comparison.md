# Technology Comparison — WITPAE Theater Staff

> **Revision 3 — supersedes all earlier drafts.**
> Analysis incorporates findings from the companion repositories
> [pywitpaescraper](https://github.com/drwilliamroney/pywitpaescraper) and
> [pywitpaeui](https://github.com/drwilliamroney/pywitpaeui), verified
> PyPI wheel availability for 32-bit Windows targets, and the explicit
> architectural constraints stated by the project owner.

---

## 1 — Confirmed Requirements

| Requirement | Source |
|---|---|
| Single self-contained application — one repo, one process | Project owner |
| 32-bit DLL (`pwsdll.dll` + `pwsdll7.dll`) called **in-process** | Project owner |
| Native desktop UI — no web-browser presentation layer | Project owner |
| Leverage logic and documentation from the companion repos | Project owner |
| 32-bit struct alignment (`_pack_` / `Pack=4` / `#pragma pack(4)`) | DLL contract |

The inter-process / subprocess architecture of the companion repos is
**explicitly rejected**: it introduces launch latency, IPC overhead, and
cross-repo debugging complexity that are unacceptable for this tool.

---

## 2 — What the Companion Repos Contribute

Both companion repos are treated as **reference implementations and
documentation**, not as runtime dependencies.  Their value is:

### From `pywitpaescraper`

| Asset | What it contributes |
|---|---|
| `pwsdll.py` — ctypes struct definitions | Complete, tested mapping of every game-record type to 32-bit-packed C structs.  This is the hardest part of the DLL integration and already works. |
| `active_models.py` — Python dataclasses | Clean data-model layer for ships, airgroupss, bases, ground units, task forces, threats. |
| `RecType`, `Side`, `Nationality`, `DeviceType` enums | All game constant enumerations. |
| `PWSDll` class | DLL loading, function-pointer declarations, open/read/close lifecycle. |
| `pywitpaescraper.py` | End-to-end record extraction and field derivation logic. |

### From `pywitpaeui`

| Asset | What it contributes |
|---|---|
| `coordinate_transform.py` | Proven linear transform: game hex → pixel. `step_x = w/(232-1)`, `step_y = h/(205-1)`. 232 × 205 grid confirmed. |
| `overlays.py` — region definitions | The eight named theater regions as `[x, y]` polygon corner coordinates. |
| `overlays.py` — overlay data builders | JSON → overlay payload logic for all seven overlay types. |
| `overlay_svg.py` / `overlay_renderer.py` | Rendering logic: geometry, colour palettes, line weights, label placement — all translatable to any rendering API. |
| `map_assembly.py` | 7 × 6 BMP tile stitch pattern (`WPEN{00..41}.bmp`). |
| HTML templates + JS | Hover-tooltip, toggle-checkbox, and click-through interaction patterns. |

---

## 3 — 32-bit Python GUI Framework Landscape

The in-process DLL constraint means the UI process **must be 32-bit (x86)**.
The following table shows what PyPI actually ships for Windows x86 today:

| Framework | Latest | win32 Python 3.10+ wheel | Notes |
|---|---|:---:|---|
| **tkinter** (stdlib) | n/a | ✅ always | Rendering severely limited (no true alpha) |
| **wxPython** | 4.2.5 | ✅ cp310–cp314 | Active 32-bit support; `wx.GraphicsContext` has full alpha |
| **PyQt5** | 5.15.11 | ⚠️ bindings only | `PyQt5-Qt5` runtime **dropped win32 after 5.15.2** → only Python 3.9 (EOL Oct 2025) |
| **PySide2** | 5.15.2.1 | ✅ but Python ≤3.10 | Qt 5.15 LTS, essentially unmaintained |
| **PySide6 / PyQt6** | 6.x | ❌ none | Qt 6 dropped 32-bit Windows entirely |
| **Pillow** | 12.x | ✅ cp310–cp314 | Image processing; rendering back-end for any framework |

**Key findings:**

- **wxPython 4.2.5** is the only actively-maintained Python GUI framework
  with confirmed win32 wheels for Python 3.10–3.14.
- **PyQt5** 32-bit is a dead end: the Qt5 runtime wheel (`PyQt5-Qt5`) stopped
  shipping win32 builds after version 5.15.2, which caps the Python version
  at 3.9 (reaching end-of-life in October 2025).
- **PySide6 / PyQt6** have no 32-bit Windows support whatsoever.

---

## 4 — Options

### Option A — Python 3.11 (32-bit) + wxPython 4.2.5

| Dimension | Detail |
|---|---|
| Python version | 3.11 x86 (32-bit) — LTS until Oct 2027 |
| GUI framework | wxPython 4.2.5 (`win32` wheel on PyPI) |
| Rendering | `wx.GraphicsContext` — full RGBA alpha, anti-aliased paths |
| Map image | Pillow assembles BMP tiles → `wx.Bitmap` via `wx.Image` |
| Overlay layers | `wx.BufferedPaintDC` + `wx.GraphicsContext` per layer |
| DLL integration | `pwsdll.py` imported directly — zero changes needed |
| Data models | `active_models.py` imported directly — zero changes needed |
| IDE | VS Code, PyCharm CE, or Visual Studio with Python plugin |
| Deployment | PyInstaller win32 target → single `.exe` |

**Pros**
- The entire `pwsdll.py` ctypes integration works as-is — 43 struct
  definitions, all DLL plumbing, all enum types — import and use immediately.
- All Python data-model code (`active_models.py`, coordinate transform,
  overlay data builders) ports with minimal edits.
- `wx.GraphicsContext` renders with true alpha transparency and sub-pixel
  anti-aliasing — not the stipple-pattern workaround tkinter requires.
- wxPython is mature, well-documented, and has been the standard Python
  desktop UI framework on Windows for two decades.
- `wx.ScrolledWindow` provides built-in scroll/pan; zoom can be implemented
  via a scale transform on the `wx.GraphicsContext`.
- One process, one repo, Python throughout.

**Cons**
- No built-in scene graph: overlay layers must be composited manually in the
  paint handler (each layer renders in z-order via `wx.GraphicsContext`).
  This is more manual than Qt's `QGraphicsScene` but entirely tractable.
- wxPython's native look can appear plain without styling effort.

**Verdict: Primary recommendation.**

---

### Option B — C# + WPF (.NET Framework 4.x, x86 platform target)

| Dimension | Detail |
|---|---|
| Language | C# 10 |
| GUI framework | WPF — `Canvas`, `DrawingVisual`, `UIElement` |
| Rendering | DirectX-backed — GPU-accelerated, full RGBA, sub-pixel AA |
| Map image | `BitmapImage` / `WriteableBitmap` from BMP tile assembly |
| Overlay layers | `DrawingVisual` or `UIElement` children of `Canvas` |
| DLL integration | P/Invoke `[DllImport]` + `[StructLayout(LayoutKind.Sequential, Pack=4)]` |
| Data models | Port `active_models.py` → C# records/classes |
| IDE | Visual Studio Community 2022 (free) |
| Deployment | ClickOnce / XCOPY; .NET Framework ships with Windows |

**Pros**
- WPF gives the best possible Windows desktop rendering quality: GPU-composited
  layers, `Opacity`, `Effect`, and CSS-like styling.
- `[StructLayout(Pack=4)]` + Roslyn analyser catches struct-size mismatches at
  compile time — the safest DLL integration path.
- Visual Studio provides a XAML designer, integrated debugger, memory profiler,
  and IntelliSense — unmatched tooling for Windows desktop.
- .NET Framework 4.x ships with every modern Windows install — no runtime
  distribution problem.
- Strong typing throughout: the compiler rejects a misnamed struct field.
- `UIElement.IsHitTestVisible`, `MouseEnter`, and `MouseDown` events implement
  the hover / click-through overlay model natively.

**Cons**
- The `pwsdll.py` DLL wrapper must be **re-implemented** in C# P/Invoke.
  The Python code documents every field precisely, making the port mechanical
  but not instant; estimate 1–2 days of careful work.
- All data models and overlay logic must be ported from Python.
- Requires C# fluency or a learning investment.
- Build step required (Roslyn compilation) — no edit-and-run.

**Verdict: Best if rendering quality and Windows integration are the top
priorities, and the team accepts a language port of the DLL wrapper.**

---

### Option C — Python 3.11 (32-bit) + tkinter + Pillow compositing

Use Pillow to composite overlays as images and display the result on a
`tkinter.Canvas` as a `PhotoImage` — effectively replicating the
`overlay_renderer.py` approach from `pywitpaeui` inside a tkinter window.

**Pros:** Works with the stdlib tkinter; Pillow win32 wheels are available.

**Cons:**
- Every mouse move or overlay toggle forces a full RGBA image composite in
  Python (slow for a 1400 × 900 map).
- No interactive scene graph: hit testing must be implemented manually from
  pixel coordinates.
- The result is a flat bitmap — no per-item hover cursor, no smooth resize.

**Verdict: Not recommended.** This is the approach of `pywitpaeui`'s
`overlay_renderer.py` — which the project owner already rejected as clunky.
Putting it inside a tkinter window rather than a browser does not fix the
underlying architectural problem.

---

### Option D — PyQt5 5.15.2 + Python 3.9 (32-bit)

**Verdict: Not recommended.** Python 3.9 reaches end-of-life in October 2025.
Building a new application on an EOL interpreter is not prudent.

---

## 5 — Recommendation

> **Use Python 3.11 (32-bit) + wxPython 4.2.5.**

This is the only path that satisfies every stated constraint simultaneously:

| Constraint | Satisfied? |
|---|:---:|
| 32-bit in-process DLL call | ✅ |
| Native desktop window (no browser) | ✅ |
| True alpha-blended overlay rendering | ✅ |
| Full reuse of `pwsdll.py` ctypes integration | ✅ |
| Full reuse of Python data models and overlay logic | ✅ |
| Supported Python version (not EOL) | ✅ |
| Available from PyPI without custom builds | ✅ |
| One repo, one process | ✅ |

If at any future point the team decides to move to a more Windows-native
technology — for richer DirectX rendering, tighter shell integration, or
commercial deployment requirements — **Option B (C# + WPF x86)** is the
natural migration target.  The DLL wrapper port is mechanical and the
`pwsdll.py` struct definitions provide an exact field-by-field template for
the C# `[StructLayout]` declarations.

---

## 6 — Architecture: One-Process Design

```
WITPAE Theater Staff  (32-bit Python 3.11 + wxPython 4.2.5)
────────────────────────────────────────────────────────────

 ┌─────────────────────────────────────────────────────────┐
 │  wx.Frame  "WITPAE Theater Staff"                        │
 │                                                          │
 │  ┌──────────────┐  ┌──────────────────────────────────┐ │
 │  │ Layer Panel  │  │  MapPanel (wx.ScrolledWindow)    │ │
 │  │              │  │                                  │ │
 │  │ [✓] Regions  │  │  wx.GraphicsContext paint:       │ │
 │  │ [✓] Bases    │  │   1. base map bitmap             │ │
 │  │ [✓] TF       │  │   2. Regions layer (alpha poly)  │ │
 │  │ [✓] Threats  │  │   3. Bases layer  (RGBA squares) │ │
 │  │ [ ] Air      │  │   4. Task Force layer (lines)    │ │
 │  │ [ ] Land     │  │   5. Threats layer (RGBA circles)│ │
 │  │ [ ] Sea      │  │                                  │ │
 │  │              │  │  Mouse events:                   │ │
 │  │              │  │   Motion → coord → tooltip       │ │
 │  │              │  │   Click  → coord → info panel    │ │
 │  └──────────────┘  └──────────────────────────────────┘ │
 │                                                          │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  InfoPanel — click-through results, all layers     │  │
 │  └────────────────────────────────────────────────────┘  │
 │  Status bar: hex (x, y) | turn | scenario                │
 └─────────────────────────────────────────────────────────┘
          │
          │ ctypes.WinDLL  (in-process, same 32-bit address space)
          ▼
   pwsdll.dll + pwsdll7.dll  (32-bit, 4-byte struct alignment)
   .pws save files  (read directly, no subprocess)
```

**Data flow (single process):**
1. User opens a `.pws` save file via `wx.FileDialog`.
2. `PWSDll` (from `pwsdll.py`) opens the file and iterates records in-process.
3. Record data populates `Active*` dataclasses (from `active_models.py`).
4. Each overlay layer queries its dataclass collection and renders via
   `wx.GraphicsContext` in the `MapPanel.on_paint` handler.
5. Mouse motion → game coordinate → all visible layers queried for
   `info_at(coord)` → tooltip drawn directly on the canvas.
6. Mouse click → same query → results displayed in `InfoPanel`.

---

## 7 — 32-bit Struct Alignment Reference

The DLL structs in `pwsdll.py` do not use `_pack_` explicitly — they rely on
the default C alignment of the 32-bit MSVC-compiled DLL.  The ctypes default
on a 32-bit interpreter already matches 4-byte packing for the types used.
If any future struct requires explicit control:

| Language | Directive | Assertion |
|---|---|---|
| Python (ctypes) | `class S(ctypes.Structure): _pack_ = 4` | `assert ctypes.sizeof(S) == N` |
| C# (if ever needed) | `[StructLayout(LayoutKind.Sequential, Pack = 4)]` | `Debug.Assert(Marshal.SizeOf<S>() == N)` |
| C++ (if ever needed) | `#pragma pack(push, 4)` / `pop` | `static_assert(sizeof(S) == N)` |

A struct-size unit test against a known-good save file is the most effective
guard against silent data corruption on any struct layout change.

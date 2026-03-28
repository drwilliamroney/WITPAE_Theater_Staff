# GitHub Copilot Instructions — WITPAE Theater Staff

## Project Context

WITPAE Theater Staff is a **32-bit Windows desktop GUI application** that assists players of
**War in the Pacific Admiral's Edition (WitPAE)**, a turn-based hex-coordinate strategy game
covering World War 2 across the entire Pacific Theater. Players take either the Japanese side
(IJArmy / IJNavy) or the Allied side (all other nations/forces defined in the game database).

### One-Process Design

The application calls the game's native **32-bit DLL** (`pwsdll.dll` + `pwsdll7.dll`)
**directly in-process** using `ctypes`.  There is no subprocess split, no web server, and
no browser window.  Everything — DLL access, data modelling, and UI rendering — runs inside
a single 32-bit Python 3.11 process.

---

## Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11 (32-bit / x86) | DLL requires 32-bit process; Python 3.11 LTS until Oct 2027 |
| **GUI framework** | **wxPython 4.2.5** | Only actively-maintained GUI framework with win32 PyPI wheels for Python 3.10+ |
| **Rendering** | `wx.GraphicsContext` | Full RGBA alpha transparency, anti-aliased paths — no stipple workarounds |
| **Map image** | Pillow 12.x | Assemble 7×6 BMP art tiles; convert to `wx.Bitmap` via `wx.Image` |
| **DLL binding** | `ctypes` (stdlib) | 32-bit in-process; structs ported from `pywitpaescraper/pwsdll.py` |
| **Logging** | `logging` + `rich` | Structured console output |

> **Do NOT use tkinter** — it has no true alpha transparency, which is required for
> semi-transparent overlay layers on the map.
>
> **Do NOT use PySide6 / PyQt6** — Qt 6 has no 32-bit Windows support.
>
> **Do NOT use PyQt5** — its 32-bit Windows support ends at Python 3.9 (EOL Oct 2025).

---

## Python Best Practices

### Code Style
- Follow **PEP 8** (4-space indentation, 88-char line limit for code, 72 for docstrings).
- Follow **PEP 257** for docstring conventions — triple double-quoted strings.
- Use **type hints** (PEP 484 / PEP 526) on all public functions, methods, and attributes.
- Use **f-strings** (PEP 498); avoid `%` formatting or `.format()`.
- Prefer `pathlib.Path` over `os.path`.
- Use `dataclasses` or `NamedTuple` for data-holding classes.
- Use `enum.Enum` for named constant sets.

### Project Structure
- Application source: `src/witpae_theater_staff/`
- Entry point: `src/witpae_theater_staff/main.py` → `main()` guarded by `if __name__ == "__main__"`.
- Module layout:
  - `dll/`       — DLL wrapper (`pwsdll.py`) and struct definitions
  - `models/`    — Active data models (`active_models.py` and derived types)
  - `map/`       — Map assembly, coordinate transform, overlay base class
  - `overlays/`  — Concrete overlay implementations (regions, bases, taskforces, threats, …)
  - `ui/`        — wx widgets: main frame, map panel, layer panel, info panel, tooltips
- Tests: `tests/` mirroring `src/`, using `pytest`.

### Imports
- Absolute imports only; no relative imports outside the same package.
- Import order: standard library → third-party (`wx`, `PIL`) → local.

### Error Handling
- Catch specific exceptions; never `except:`.
- Log with `logging`, not `print`.

---

## wxPython Conventions

### Layout
- Use `wx.BoxSizer` / `wx.GridBagSizer` for all layout.  Never use `.SetPosition()` or
  `.SetSize()` directly on a child widget.
- The main frame uses a horizontal `wx.BoxSizer`: left layer panel | centre map panel.
- An `InfoPanel` sits below the map panel in a vertical sizer.

### Map Canvas (`MapPanel`)
- Subclass `wx.ScrolledWindow`.
- Override `on_paint(event)` bound to `wx.EVT_PAINT`.
- Use `wx.AutoBufferedPaintDC` (prevents flicker).
- Obtain a `wx.GraphicsContext` from the DC for all overlay drawing.
- Bind `wx.EVT_MOTION` for hover tooltips, `wx.EVT_LEFT_DOWN` for click-through.

### Rendering with wx.GraphicsContext
```python
def on_paint(self, event: wx.PaintEvent) -> None:
    dc = wx.AutoBufferedPaintDC(self)
    gc = wx.GraphicsContext.Create(dc)
    # Draw base map
    gc.DrawBitmap(self._base_bitmap, 0, 0, w, h)
    # Draw each visible overlay (bottom to top)
    for overlay in self._overlay_manager.visible_layers:
        overlay.render(gc, self._transform)
```

### Alpha transparency
Use `wx.GraphicsContext` methods that accept `wx.Colour` with an alpha component (0–255):
```python
fill = wx.Colour(100, 149, 237, 64)   # cornflower blue, 25 % opacity
pen  = wx.Colour(100, 149, 237, 178)  # same colour, 70 % opacity
gc.SetBrush(gc.CreateBrush(wx.Brush(fill)))
gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(pen).Width(2)))
gc.DrawRectangle(x, y, w, h)
```

### Tooltip on hover
Draw the tooltip directly onto the canvas (not a `wx.ToolTip` or popup window):
```python
def _draw_tooltip(self, gc: wx.GraphicsContext, text: str, x: float, y: float) -> None:
    # measure, draw background rect, draw text
    ...
```

### Layer toggle panel
- `wx.CheckListBox` or a vertical list of `wx.CheckBox` widgets, one per overlay.
- Toggling a checkbox calls `overlay.visible = checked` then `self._map_panel.Refresh()`.

### Main window title
The `wx.Frame` title must always be **"WITPAE Theater Staff"**.

---

## Coordinate System

WitPAE uses a **232 × 205 rectangular grid** (1-indexed).  There is no hexagonal
offset geometry — the "hex" appearance is baked into the BMP map art.

```python
# game_coords.py
GAME_COLS = 232   # x ∈ [1, 232]
GAME_ROWS = 205   # y ∈ [1, 205]

step_x = canvas_width  / (GAME_COLS - 1)
step_y = canvas_height / (GAME_ROWS - 1)

# top-left corner of hex cell (for region polygon vertices)
pixel_x = (game_x - 1) * step_x
pixel_y = (game_y - 1) * step_y

# visual centre of hex cell (for point markers, lines)
center_x = pixel_x + step_x / 2
center_y = pixel_y + step_y / 2
```

---

## Overlay Architecture (Acetate-Sheet Model)

Each overlay is an independent layer, analogous to an acetate sheet on a paper map:

```python
class Overlay(ABC):
    name: str
    visible: bool

    @abstractmethod
    def render(self, gc: wx.GraphicsContext, transform: GameCoordTransform) -> None:
        """Draw onto gc.  All items MUST be re-drawn on every paint cycle."""

    @abstractmethod
    def info_at(self, coord: GameCoord) -> str | None:
        """Return hover/click info for coord, or None."""
```

`OverlayManager` maintains a z-ordered list.  `render_all()` draws visible layers
bottom-first.  `info_at()` walks **top-to-bottom** (click-through: all layers
contribute, not just the topmost).

---

## DLL Integration

The DLL wrapper is ported from `pywitpaescraper/pwsdll.py`.  Key rules:

- All structs **must** match the 32-bit MSVC layout of the DLL exactly.
- Use `ctypes.WinDLL` (stdcall convention) — never `ctypes.CDLL`.
- Add `assert ctypes.sizeof(StructName) == EXPECTED_BYTES` after every struct
  definition as a layout regression guard.
- Load the DLL **after** calling `os.add_dll_directory(dll_dir)` so the loader
  can resolve `pwsdll7.dll` as a dependency of `pwsdll.dll`.

---

## Legacy Reference Repos

The following repos are **reference / documentation** — not runtime dependencies:

| Repo | What to port |
|---|---|
| `pywitpaescraper` | `pwsdll.py` structs and enums; `active_models.py` dataclasses; extraction logic |
| `pywitpaeui` | `coordinate_transform.py`; region polygon coordinates; overlay colour palettes and geometry from `overlays.py`, `overlay_svg.py`, `overlay_renderer.py` |

---

## Domain Vocabulary

| Term | Meaning |
|---|---|
| hex / hex coord | A rectangular grid cell on the WitPAE map, identified by (x, y) where x ∈ [1, 232], y ∈ [1, 205] |
| IJArmy / IJNavy | Imperial Japanese Army / Navy |
| Allied | All non-Japanese forces (US, UK, ANZAC, Dutch, Chinese, etc.) |
| LCU | Land Combat Unit |
| TF | Task Force (naval) |
| Base | A named location that can be a supply hub, airfield, or port |
| pwsdll | The 32-bit game DLL that exposes save-file data |
| pws file | A `.pws` WitPAE save file (e.g. `wpae000.pws`) |

---

## Dependencies

Pin all third-party dependencies in `requirements.txt` using `==` version specifiers.
The virtual environment is created and managed by `run_gui.bat`; never commit `.venv/`.

Current pinned versions:
```
wxPython==4.2.5
Pillow==12.1.1
rich>=13.0.0
```

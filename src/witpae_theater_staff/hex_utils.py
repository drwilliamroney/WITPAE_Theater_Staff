"""Hex-grid coordinate utilities for WITPAE Theater Staff.

WitPAE uses a **flat-topped** hex grid with an **odd-column vertical offset**:
odd columns (col & 1 == 1) are shifted downward by half a hex-height relative
to even columns.

Coordinate system
-----------------
- ``col`` increases to the East.
- ``row`` increases to the South.
- ``(0, 0)`` is the top-left hex.

Flat-top geometry (one hex, center at origin)::

          *─────*
         /       \\
        *         *      ← corners at 0°, 60°, 120°, 180°, 240°, 300°
         \\       /
          *─────*

Width  (tip-to-tip, horizontal) = 2 × size
Height (flat-to-flat, vertical) = √3 × size

Column center spacing (horizontal): 1.5 × size
Row center spacing   (vertical):    √3  × size
Odd-column downward offset:         (√3 / 2) × size
"""

import math
from typing import NamedTuple


class HexCoord(NamedTuple):
    """An (col, row) hex-grid coordinate."""

    col: int
    row: int


class HexGrid:
    """Geometry engine for a flat-topped, odd-column-offset hex grid.

    Parameters
    ----------
    hex_size:
        Circumradius of each hex in pixels (center → corner).
    origin_x:
        Canvas x-pixel of the center of hex (0, 0).
    origin_y:
        Canvas y-pixel of the center of hex (0, 0).
    """

    def __init__(
        self,
        hex_size: float = 32.0,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ) -> None:
        self.hex_size: float = hex_size
        self.origin_x: float = origin_x
        self.origin_y: float = origin_y

    # ── Derived geometry ──────────────────────────────────────────────────────

    @property
    def col_spacing(self) -> float:
        """Horizontal distance (pixels) between adjacent column centers."""
        return 1.5 * self.hex_size

    @property
    def row_spacing(self) -> float:
        """Vertical distance (pixels) between row centers in the same column."""
        return math.sqrt(3.0) * self.hex_size

    @property
    def odd_col_offset(self) -> float:
        """Downward pixel shift applied to odd columns."""
        return self.row_spacing / 2.0

    # ── Coordinate conversion ─────────────────────────────────────────────────

    def hex_center(self, col: int, row: int) -> tuple[float, float]:
        """Return pixel ``(x, y)`` of the centre of hex ``(col, row)``."""
        x = self.origin_x + col * self.col_spacing
        y = self.origin_y + row * self.row_spacing
        if col & 1:
            y += self.odd_col_offset
        return (x, y)

    def pixel_to_hex(self, px: float, py: float) -> HexCoord:
        """Return the hex ``(col, row)`` that contains pixel ``(px, py)``.

        Uses a nearest-centre search across candidate columns to handle
        the irregular boundaries of flat-top hexes robustly.
        """
        # Rough column estimate from x alone
        approx_col = (px - self.origin_x) / self.col_spacing
        col_guess = int(round(approx_col))

        best = HexCoord(col_guess, 0)
        best_dist2 = float("inf")

        # Check the guessed column and its immediate neighbours to handle
        # boundary cases where the nearest centre is in an adjacent column.
        for col in (col_guess - 1, col_guess, col_guess + 1):
            ry = py - self.origin_y
            if col & 1:
                ry -= self.odd_col_offset
            row = int(round(ry / self.row_spacing))
            d2 = self._dist2(px, py, col, row)
            if d2 < best_dist2:
                best_dist2 = d2
                best = HexCoord(col, row)

        return best

    def _dist2(self, px: float, py: float, col: int, row: int) -> float:
        """Squared pixel distance from ``(px, py)`` to the centre of ``(col, row)``."""
        cx, cy = self.hex_center(col, row)
        return (px - cx) ** 2 + (py - cy) ** 2

    # ── Corner vertices ───────────────────────────────────────────────────────

    def hex_corners(self, col: int, row: int) -> list[tuple[float, float]]:
        """Return the six corner pixel coordinates of hex ``(col, row)``.

        Corners are listed starting at 0° (right-most) and advancing by
        60° steps (counter-clockwise in standard maths coordinates, which
        appears clockwise on a tkinter canvas where y increases downward).
        """
        cx, cy = self.hex_center(col, row)
        return [
            (
                cx + self.hex_size * math.cos(math.radians(60 * i)),
                cy + self.hex_size * math.sin(math.radians(60 * i)),
            )
            for i in range(6)
        ]

    def hex_polygon(self, col: int, row: int) -> list[float]:
        """Return a flat ``[x0, y0, x1, y1, …]`` list for ``Canvas.create_polygon``."""
        coords: list[float] = []
        for x, y in self.hex_corners(col, row):
            coords.extend((x, y))
        return coords

    # ── Neighbour lookup ──────────────────────────────────────────────────────

    def neighbors(self, col: int, row: int) -> list[HexCoord]:
        """Return the six neighbours of hex ``(col, row)``.

        Direction tables follow the flat-top, odd-column-offset convention
        (odd columns shifted downward by half a row).
        """
        if col & 1:  # odd column
            deltas = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (0, -1)]
        else:         # even column
            deltas = [(1, -1), (1, 0), (0, 1), (-1, 0), (-1, -1), (0, -1)]
        return [HexCoord(col + dc, row + dr) for dc, dr in deltas]

    # ── Visible-hex range ─────────────────────────────────────────────────────

    def visible_hex_range(
        self,
        viewport_width: float,
        viewport_height: float,
    ) -> tuple[range, range]:
        """Return ``(col_range, row_range)`` of hexes visible in the viewport.

        The viewport is assumed to start at the grid origin ``(origin_x, origin_y)``.
        Both ranges include one extra hex on each edge as a rendering buffer.
        """
        max_col = int(viewport_width / max(self.col_spacing, 1.0)) + 2
        max_row = int(viewport_height / max(self.row_spacing, 1.0)) + 2
        return range(0, max_col), range(0, max_row)

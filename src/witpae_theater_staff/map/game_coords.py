"""WitPAE game-hex coordinate transform.

The WitPAE map is a **232 × 205 rectangular grid** of named hex cells.
Game coordinates are 1-indexed integers: ``x ∈ [1, 232]``, ``y ∈ [1, 205]``.

Pixel position is a purely linear function — there is no hexagonal offset
geometry; the "hex" appearance is baked into the BMP map art tiles.

References
----------
- ``pywitpaeui / app / coordinate_transform.py`` — ``GameHexTransform``
- ``pywitpaeui / app / overlays.py`` — ``GAME_COLS = 232``, ``GAME_ROWS = 205``
"""

from typing import NamedTuple

# ── Map grid constants ────────────────────────────────────────────────────────

GAME_COLS: int = 232
"""Number of hex columns in the WitPAE map (x ∈ [1, 232])."""

GAME_ROWS: int = 205
"""Number of hex rows in the WitPAE map (y ∈ [1, 205])."""


class GameCoord(NamedTuple):
    """A 1-indexed WitPAE game-hex coordinate pair."""

    x: int
    """Column — 1 = westernmost, 232 = easternmost."""

    y: int
    """Row — 1 = northernmost, 205 = southernmost."""


class GameCoordTransform:
    """Convert between WitPAE game-hex coordinates and canvas pixel coordinates.

    Instantiate a new transform whenever the canvas is resized; the object is
    lightweight and cheap to reconstruct.

    Parameters
    ----------
    canvas_width:
        Current canvas width in pixels.
    canvas_height:
        Current canvas height in pixels.
    """

    def __init__(self, canvas_width: float, canvas_height: float) -> None:
        self._w: float = max(canvas_width, 1.0)
        self._h: float = max(canvas_height, 1.0)

    # ── Derived step sizes ────────────────────────────────────────────────────

    @property
    def step_x(self) -> float:
        """Horizontal pixel span per game column."""
        return self._w / (GAME_COLS - 1)

    @property
    def step_y(self) -> float:
        """Vertical pixel span per game row."""
        return self._h / (GAME_ROWS - 1)

    # ── Forward: game → canvas ────────────────────────────────────────────────

    def to_canvas(self, x: int, y: int) -> tuple[float, float]:
        """Canvas pixel at the **top-left corner** of game hex ``(x, y)``.

        Use for region boundary polygon vertices — matches
        ``gamehex_to_pixel`` in ``pywitpaeui``.
        """
        return (x - 1) * self.step_x, (y - 1) * self.step_y

    def to_canvas_center(self, x: int, y: int) -> tuple[float, float]:
        """Canvas pixel at the **visual centre** of game hex ``(x, y)``.

        Use for point-on-hex markers, lines, and labels — matches
        ``gamehex_to_hex_center`` in ``pywitpaeui``.
        """
        px, py = self.to_canvas(x, y)
        return px + self.step_x / 2.0, py + self.step_y / 2.0

    def polygon_to_canvas(self, points: list[list[int]]) -> list[tuple[float, float]]:
        """Convert ``[[x, y], …]`` game-hex corner points to canvas coordinates.

        Uses ``to_canvas`` (top-left corner) — correct for region polygons.
        Returns a list of ``(px, py)`` tuples suitable for
        ``gc.DrawLines()`` or ``gc.DrawPath()``.
        """
        return [self.to_canvas(x, y) for x, y in points]

    # ── Inverse: canvas → game ────────────────────────────────────────────────

    def to_game(self, px: float, py: float) -> GameCoord:
        """Game hex ``(x, y)`` containing canvas pixel ``(px, py)``.

        Clamped to the valid map range ``[1, GAME_COLS] × [1, GAME_ROWS]``.
        """
        x = round(px / self.step_x) + 1
        y = round(py / self.step_y) + 1
        return GameCoord(
            x=max(1, min(GAME_COLS, x)),
            y=max(1, min(GAME_ROWS, y)),
        )

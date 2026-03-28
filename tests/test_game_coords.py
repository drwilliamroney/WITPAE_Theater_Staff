"""Unit tests for the WitPAE game-hex coordinate transform.

These tests are framework-agnostic (no wx import) and run in any Python
environment, including the headless CI runner.
"""

import pytest

from witpae_theater_staff.map.game_coords import (
    GAME_COLS,
    GAME_ROWS,
    GameCoord,
    GameCoordTransform,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def transform_1400x900() -> GameCoordTransform:
    """Transform matching the pywitpaeui default map resolution (1400 × 900)."""
    return GameCoordTransform(1400, 900)


@pytest.fixture
def transform_square() -> GameCoordTransform:
    return GameCoordTransform(1000, 1000)


# ── Constants ─────────────────────────────────────────────────────────────────


def test_game_dimensions() -> None:
    assert GAME_COLS == 232
    assert GAME_ROWS == 205


# ── Step sizes ────────────────────────────────────────────────────────────────


def test_step_x(transform_1400x900: GameCoordTransform) -> None:
    expected = 1400 / (232 - 1)
    assert transform_1400x900.step_x == pytest.approx(expected)


def test_step_y(transform_1400x900: GameCoordTransform) -> None:
    expected = 900 / (205 - 1)
    assert transform_1400x900.step_y == pytest.approx(expected)


# ── to_canvas: top-left corner ────────────────────────────────────────────────


def test_to_canvas_origin(transform_1400x900: GameCoordTransform) -> None:
    """Game hex (1, 1) maps to canvas (0, 0)."""
    px, py = transform_1400x900.to_canvas(1, 1)
    assert px == pytest.approx(0.0)
    assert py == pytest.approx(0.0)


def test_to_canvas_max(transform_1400x900: GameCoordTransform) -> None:
    """Game hex (232, 205) maps to canvas (width, height)."""
    px, py = transform_1400x900.to_canvas(232, 205)
    assert px == pytest.approx(1400.0)
    assert py == pytest.approx(900.0)


def test_to_canvas_midpoint(transform_square: GameCoordTransform) -> None:
    """Midpoint of the grid is midpoint of the canvas."""
    mid_x = (GAME_COLS + 1) // 2   # 117
    mid_y = (GAME_ROWS + 1) // 2   # 103
    px, py = transform_square.to_canvas(mid_x, mid_y)
    step_x = 1000 / (GAME_COLS - 1)
    step_y = 1000 / (GAME_ROWS - 1)
    assert px == pytest.approx((mid_x - 1) * step_x)
    assert py == pytest.approx((mid_y - 1) * step_y)


# ── to_canvas_center ─────────────────────────────────────────────────────────


def test_to_canvas_center_offset(transform_1400x900: GameCoordTransform) -> None:
    """Centre is offset from top-left by exactly half a step."""
    px_tl, py_tl = transform_1400x900.to_canvas(5, 10)
    px_c, py_c = transform_1400x900.to_canvas_center(5, 10)
    assert px_c == pytest.approx(px_tl + transform_1400x900.step_x / 2)
    assert py_c == pytest.approx(py_tl + transform_1400x900.step_y / 2)


# ── to_game: inverse transform ────────────────────────────────────────────────


def test_to_game_origin(transform_1400x900: GameCoordTransform) -> None:
    assert transform_1400x900.to_game(0.0, 0.0) == GameCoord(1, 1)


def test_to_game_max(transform_1400x900: GameCoordTransform) -> None:
    assert transform_1400x900.to_game(1400.0, 900.0) == GameCoord(232, 205)


def test_round_trip(transform_1400x900: GameCoordTransform) -> None:
    """to_canvas followed by to_game should return the original coordinate."""
    for x, y in [(1, 1), (1, 205), (232, 1), (232, 205), (50, 100), (116, 102)]:
        px, py = transform_1400x900.to_canvas_center(x, y)
        assert transform_1400x900.to_game(px, py) == GameCoord(x, y), (
            f"Round-trip failed for ({x}, {y})"
        )


def test_to_game_clamping_low(transform_1400x900: GameCoordTransform) -> None:
    """Negative pixel coordinates clamp to (1, 1)."""
    assert transform_1400x900.to_game(-100.0, -100.0) == GameCoord(1, 1)


def test_to_game_clamping_high(transform_1400x900: GameCoordTransform) -> None:
    """Over-range pixel coordinates clamp to (GAME_COLS, GAME_ROWS)."""
    assert transform_1400x900.to_game(9999.0, 9999.0) == GameCoord(232, 205)


# ── polygon_to_canvas ─────────────────────────────────────────────────────────


def test_polygon_to_canvas_length(transform_1400x900: GameCoordTransform) -> None:
    points = [[1, 1], [232, 1], [232, 205], [1, 205]]
    result = transform_1400x900.polygon_to_canvas(points)
    assert len(result) == 4


def test_polygon_to_canvas_corners(transform_1400x900: GameCoordTransform) -> None:
    points = [[1, 1], [232, 205]]
    result = transform_1400x900.polygon_to_canvas(points)
    assert result[0] == pytest.approx((0.0, 0.0))
    assert result[1] == pytest.approx((1400.0, 900.0))


# ── Degenerate canvas sizes ────────────────────────────────────────────────────


def test_zero_canvas_does_not_divide_by_zero() -> None:
    """GameCoordTransform clamps to min 1.0 so no ZeroDivisionError."""
    t = GameCoordTransform(0, 0)
    px, py = t.to_canvas(1, 1)
    assert px == pytest.approx(0.0)
    assert py == pytest.approx(0.0)

"""Region overlay definitions aligned with pywitpaeui."""

from __future__ import annotations

from dataclasses import dataclass


GAME_COLS = 232
GAME_ROWS = 205


@dataclass(frozen=True)
class RegionDefinition:
    """Named theater region in game-hex coordinates."""

    name: str
    abbr: str
    fill_rgba: tuple[int, int, int, int]
    border_rgba: tuple[int, int, int, int]
    polygon_hex: tuple[tuple[int, int], ...]


REGION_DEFINITIONS: tuple[RegionDefinition, ...] = (
    RegionDefinition(
        name="North Pacific",
        abbr="NOPAC",
        fill_rgba=(100, 149, 237, 64),
        border_rgba=(100, 149, 237, 178),
        polygon_hex=((88, 1), (GAME_COLS, 1), (GAME_COLS, 55), (88, 55)),
    ),
    RegionDefinition(
        name="Central Pacific",
        abbr="CENPAC",
        fill_rgba=(0, 200, 255, 51),
        border_rgba=(0, 200, 255, 178),
        polygon_hex=((96, 55), (GAME_COLS, 55), (GAME_COLS, 120), (96, 120)),
    ),
    RegionDefinition(
        name="South Pacific",
        abbr="SOPAC",
        fill_rgba=(0, 200, 100, 51),
        border_rgba=(0, 200, 100, 178),
        polygon_hex=((106, 120), (GAME_COLS, 120), (GAME_COLS, GAME_ROWS), (106, GAME_ROWS)),
    ),
    RegionDefinition(
        name="Southwest Pacific",
        abbr="SWPAC",
        fill_rgba=(255, 165, 0, 51),
        border_rgba=(255, 165, 0, 178),
        polygon_hex=((40, 120), (106, 120), (106, GAME_ROWS), (40, GAME_ROWS)),
    ),
    RegionDefinition(
        name="Netherlands East Indies",
        abbr="NEI",
        fill_rgba=(200, 100, 220, 51),
        border_rgba=(200, 100, 220, 178),
        polygon_hex=((40, 87), (96, 87), (96, 120), (40, 120)),
    ),
    RegionDefinition(
        name="Philippines / Malaya",
        abbr="PHIL",
        fill_rgba=(220, 50, 50, 51),
        border_rgba=(220, 50, 50, 178),
        polygon_hex=((40, 55), (96, 55), (96, 87), (40, 87)),
    ),
    RegionDefinition(
        name="China-Burma-India",
        abbr="CBI",
        fill_rgba=(240, 220, 0, 51),
        border_rgba=(240, 220, 0, 178),
        polygon_hex=((1, 1), (88, 1), (88, 55), (1, 55)),
    ),
    RegionDefinition(
        name="Indian Ocean",
        abbr="IO",
        fill_rgba=(0, 180, 180, 51),
        border_rgba=(0, 180, 180, 178),
        polygon_hex=((1, 55), (40, 55), (40, GAME_ROWS), (1, GAME_ROWS)),
    ),
)

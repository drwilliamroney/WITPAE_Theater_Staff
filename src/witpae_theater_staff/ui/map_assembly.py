"""Assemble the Pacific theater base map from game BMP tile files.

The game ships 42 tiles (7 columns × 6 rows) named ``WPEN00.bmp`` …
``WPEN41.bmp`` in its ``ART`` subdirectory.  This module stitches them into
a single ``PIL.Image`` that the map canvas uses as its background.

A placeholder image is returned when the game directory is absent or the
tiles cannot be found, allowing the application to run without a game
installation (useful for development and testing).
"""

from __future__ import annotations

import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)

_TILE_COLS = 7
_TILE_ROWS = 6
_TILE_PATTERN = "WPEN{:02d}.bmp"


def assemble_map(game_dir: Path | None) -> "PIL.Image.Image":
    """Return the assembled map image.

    Tries to load tiles from ``game_dir/ART/``.  Falls back to a placeholder
    ocean-blue image if tiles are not available.

    Parameters
    ----------
    game_dir:
        Root WITPAE installation directory (the one containing the DLLs).
    """
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415 — lazy import

    if game_dir is not None:
        art_dir = Path(game_dir) / "ART"
        image = _try_from_tiles(art_dir)
        if image is not None:
            LOGGER.info("Map assembled from %d tiles in %s", _TILE_COLS * _TILE_ROWS, art_dir)
            return image

    LOGGER.warning("Map tiles not found; using placeholder.")
    return _placeholder()


def _try_from_tiles(art_dir: Path) -> "PIL.Image.Image | None":
    from PIL import Image  # noqa: PLC0415

    try:
        if not art_dir.is_dir():
            return None

        tile_paths = [
            art_dir / _TILE_PATTERN.format(i)
            for i in range(_TILE_COLS * _TILE_ROWS)
        ]
        if not all(p.exists() for p in tile_paths):
            missing = [p.name for p in tile_paths if not p.exists()]
            LOGGER.debug("Missing tile files: %s", missing[:5])
            return None

        tiles: list[Image.Image] = []
        for path in tile_paths:
            with Image.open(path) as img:
                tiles.append(img.copy())

        # Account for edge tiles that may be narrower/shorter
        col_widths = [0] * _TILE_COLS
        row_heights = [0] * _TILE_ROWS
        for idx, tile in enumerate(tiles):
            row = idx // _TILE_COLS
            col = idx % _TILE_COLS
            col_widths[col] = max(col_widths[col], tile.width)
            row_heights[row] = max(row_heights[row], tile.height)

        x_offsets = [0] * _TILE_COLS
        y_offsets = [0] * _TILE_ROWS
        for col in range(1, _TILE_COLS):
            x_offsets[col] = x_offsets[col - 1] + col_widths[col - 1]
        for row in range(1, _TILE_ROWS):
            y_offsets[row] = y_offsets[row - 1] + row_heights[row - 1]

        composite_w = sum(col_widths)
        composite_h = sum(row_heights)
        composite = Image.new("RGB", (composite_w, composite_h))
        for idx, tile in enumerate(tiles):
            row = idx // _TILE_COLS
            col = idx % _TILE_COLS
            composite.paste(tile, (x_offsets[col], y_offsets[row]))

        return composite

    except Exception:
        LOGGER.exception("Failed to assemble map from tiles in %s", art_dir)
        return None


def _placeholder() -> "PIL.Image.Image":
    from PIL import Image, ImageDraw  # noqa: PLC0415

    w, h = 1400, 900
    image = Image.new("RGB", (w, h), color=(20, 36, 64))
    draw = ImageDraw.Draw(image)
    draw.rectangle([(12, 12), (w - 13, h - 13)], outline=(100, 140, 200), width=2)
    # Draw a simple grid to suggest the hex map
    for gx in range(0, w, 100):
        draw.line([(gx, 0), (gx, h)], fill=(30, 50, 85), width=1)
    for gy in range(0, h, 100):
        draw.line([(0, gy), (w, gy)], fill=(30, 50, 85), width=1)
    draw.text(
        (w // 2 - 220, h // 2 - 12),
        "WITPAE Map — tiles not found (placeholder)",
        fill=(200, 220, 255),
    )
    return image

"""Map assembly utilities for stitching WITPAE tile art."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class MapAssembly:
    """Assemble the game theater map from WPEN tile images."""

    TILE_COLS = 7
    TILE_ROWS = 6
    TILE_PATTERN = "WPEN{:02d}.bmp"

    def __init__(self, game_dir: Path | None) -> None:
        self._image, self._from_tiles = self._load(game_dir)

    @property
    def image(self) -> Image.Image:
        """Return the assembled map image."""
        return self._image

    @property
    def from_tiles(self) -> bool:
        """Return whether the map came from real game tiles."""
        return self._from_tiles

    def _load(self, game_dir: Path | None) -> tuple[Image.Image, bool]:
        if game_dir is not None:
            art_dir = game_dir / "ART"
            image = self._try_from_dir(art_dir)
            if image is not None:
                logger.info("Map assembled from tiles in %s", art_dir)
                return image, True

        logger.warning("Map tiles not found; using placeholder map")
        return self._placeholder(), False

    def _try_from_dir(self, art_dir: Path) -> Image.Image | None:
        try:
            if not art_dir.is_dir():
                return None

            tile_paths = [art_dir / self.TILE_PATTERN.format(i) for i in range(self.TILE_COLS * self.TILE_ROWS)]
            if not all(path.exists() for path in tile_paths):
                return None

            tiles: list[Image.Image] = []
            for tile_path in tile_paths:
                with Image.open(tile_path) as tile_image:
                    tiles.append(tile_image.convert("RGB"))

            col_widths = [0] * self.TILE_COLS
            row_heights = [0] * self.TILE_ROWS
            for idx, tile in enumerate(tiles):
                row = idx // self.TILE_COLS
                col = idx % self.TILE_COLS
                col_widths[col] = max(col_widths[col], tile.width)
                row_heights[row] = max(row_heights[row], tile.height)

            x_offsets = [0] * self.TILE_COLS
            y_offsets = [0] * self.TILE_ROWS
            for col in range(1, self.TILE_COLS):
                x_offsets[col] = x_offsets[col - 1] + col_widths[col - 1]
            for row in range(1, self.TILE_ROWS):
                y_offsets[row] = y_offsets[row - 1] + row_heights[row - 1]

            composite = Image.new("RGB", (sum(col_widths), sum(row_heights)))
            for idx, tile in enumerate(tiles):
                row = idx // self.TILE_COLS
                col = idx % self.TILE_COLS
                composite.paste(tile, (x_offsets[col], y_offsets[row]))
            return composite
        except Exception:
            logger.exception("Failed to assemble map from %s", art_dir)
            return None

    def _placeholder(self) -> Image.Image:
        image = Image.new("RGB", (1400, 900), color=(20, 36, 64))
        draw = ImageDraw.Draw(image)
        draw.rectangle([(15, 15), (1385, 885)], outline=(150, 180, 220), width=2)
        draw.text((30, 30), "WITPAE Base Map - tiles not found", fill=(240, 240, 240))
        return image

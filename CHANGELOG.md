# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Added
- Added **Transport TF** overlay under the Ground section of the overlays dock, showing movement lines for TRANSPORT, FASTTRANSPORT, and AMPHIB mission task forces.
- `run_ui.bat` and `run_ui.ps1` now perform a `git pull` at startup to fetch the latest code before launching; if git is unavailable or the pull fails the scripts warn and continue with the existing local code.

### Changed
- Removed TRANSPORT, FASTTRANSPORT, and AMPHIB missions from the **Other TF** overlay (Surface section); they now appear exclusively in the new **Transport TF** overlay under Ground.

### Fixed
- Fixed startup `AttributeError: 'MainWindow' object has no attribute '_update_tf_legend'` crash caused by a missing `def _update_tf_legend(self) -> None:` method header; the method body was present but unreachable.
- Fixed startup `AttributeError: type object 'MainWindow' has no attribute 'GAME_EXECUTABLE'` crash when opening the Startup Game dialog by adding the missing `GAME_EXECUTABLE = "witpae.exe"` class attribute.
- Fixed startup `NameError: name 'color' is not defined` crash in `_build_logistics_taskforces_overlay` — the call to `_draw_taskforce_line` now correctly passes `color=line_color`.
- Restored the missing for-loop body in `_build_cv_tfs_overlay` (coordinate extraction, line drawing, `drawn` counter, and post-loop legend/log) that had been accidentally truncated.
- Removed orphaned logistics TF drawing code that had ended up inside `_update_tf_legend`'s `if self._map_view` block, causing a second potential `NameError` whenever the legend was updated.
- Added CV TFs and Other TF surface overlay checkboxes to the Surface mode section of the overlays dock.
- CV TFs overlay draws movement lines (start-of-day to end-of-day with arrowhead, dashed line to target destination) for all AIRCOMBAT-mission task forces.
- Other TF overlay draws per-type colored movement lines for all task forces excluding air-combat, cargo, replenishment, tanker, and sub-patrol missions.
- Added lower-right map legend overlay that appears when CV TFs or Other TF layers are enabled, showing a color swatch and label for each mission type present in the loaded data.
- Added logistics overlays panel (Logistics section in left dock):
  - **Task Forces** overlay: draws movement lines (start→end of day) for CARGO, TANKER, and REPLENISHMENT task forces in distinct colors (blue/yellow/green) with a map legend showing mission type and count.
  - **Bases** overlay: draws base status markers color-coded by port level (gold for major, blue for large, green for medium, grey for minor) with red tint for significant damage and orange tint for critically low supply.
- Added `_extract_bases_from_snapshots()` to `runtime_scraper.py` for in-memory base data extraction from end-of-day snapshot without writing JSON files.
- Added in-memory `bases` dataset to `scrape_snapshot()` output for overlay consumption.
- Added in-process legacy scraper bridge for runtime snapshot loading directly from game files in the GUI.
- Added startup and end-turn scraper refresh hooks so overlays rebuild from current turn data.
- Added left docked overlays explorer with grouped sections and submarine-specific layer controls.
- Added editable startup game launch dialog in the desktop app shell.
- Added map view dropdown replacing the "Full Map" button; top item is Full Map (default), followed by each named region; selecting a region zooms the canvas so the region fills the viewport width with its top-left anchored at the canvas top-left.

### Changed
- Changed startup map behavior to fit to full map width after layout initialization.
- Changed side normalization and runtime parsing paths to consistently map ALLIED and JAPAN data.
- Changed taskforce extraction to mirror legacy snapshot/export behavior in-memory for parity.
- Changed hex calibration workflow and documented 42x38 coordinate alignment process.

### Fixed
- Fixed mismatch where in-process taskforces and SUBPATROL counts diverged from legacy scraper output.
- Fixed coordinate extraction for text patterns using at x,y in addition to parenthesized coordinates.
- Fixed launcher startup path contamination in run_ui.ps1 by suppressing bootstrap command noise.
- Fixed app startup and launch behavior during the PyQt5 migration phase.

## [2026-04-04] - Retroactive Baseline

### Added
- Migrated repository to Python desktop architecture with PyQt5 UI shell and launcher scripts.
- Introduced startup game launch controls and map calibration utilities used by the current application.

### Changed
- Standardized map-first presentation and overlay rendering pipeline around runtime in-memory datasets.

### Fixed
- Resolved multiple startup, environment, and runtime integration issues while transitioning from legacy implementation paths.

# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Added
- Added CV TFs and Other TF surface overlay checkboxes to the Surface mode section of the overlays dock.
- CV TFs overlay draws movement lines (start-of-day to end-of-day with arrowhead, dashed line to target destination) for all AIRCOMBAT-mission task forces.
- Other TF overlay draws per-type colored movement lines for all task forces excluding air-combat, cargo, replenishment, tanker, and sub-patrol missions.
- Added lower-right map legend overlay that appears when CV TFs or Other TF layers are enabled, showing a color swatch and label for each mission type present in the loaded data.
- Added in-process legacy scraper bridge for runtime snapshot loading directly from game files in the GUI.
- Added startup and end-turn scraper refresh hooks so overlays rebuild from current turn data.
- Added left docked overlays explorer with grouped sections and submarine-specific layer controls.
- Added editable startup game launch dialog in the desktop app shell.

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

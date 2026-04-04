# WITPAE Theater Staff

A local Windows desktop UI for War in the Pacific: Admiral's Edition.

This repository now targets a single-process Python architecture using PyQt5 and
32-bit Python 3.13 so game DLLs can be called in-process.

## Requirements

- Windows
- Python 3.13 **32-bit**
- Game installation directory containing:
  - `pwsdll.dll`
  - `pwsdll7.dll`

## Quick Start

### Batch launcher

```bat
run_ui.bat
```

### PowerShell launcher

```powershell
.\run_ui.ps1
```

Both launchers:

1. Verify Python is x86 and exactly 3.13
2. Verify required game DLLs are present in the provided game directory
3. Create `.venv` if needed
4. Install dependencies from `requirements.txt`
5. Start the PyQt5 UI

If Python x86 3.13 is not found, the script prints installation guidance.

Python 3.14 x86 is not currently supported because `PyQt5` wheels are not
available for this project target yet.

## Current UI Scope

- Main window title: `WITPAE Theater Staff`
- Base map assembled from `ART\WPEN00.bmp` to `ART\WPEN41.bmp`
- Placeholder map fallback when tiles are missing
- Top bar runtime metadata sourced from scraper `SAVE/<SIDE>/turn.json`:
  scenario name, game date, and turn number
- Collapsible overlays panel with grouped layers:
  - Common
  - Logistics
  - Combat
  - Sea
  - Air
  - Land
- Full map reset button in the overlays panel
- Overlay layers are rebuilt automatically after turn processing and respect
  user toggle visibility state

## Overlay Capabilities (Current)

The overlays are now driven from pywitpaeui/pywitpaescraper-style JSON outputs
under `SAVE/ALLIED` or `SAVE/JAPAN`.

### Common layers

- `Regions`
  - Source: static theater region definitions (`app/regions_overlay.py`)
  - Shows: named theater boundaries

- `HexGrid`
  - Source: calibrated map constants (`app/main_window.py`)
  - Shows: full map hex lattice aligned to game coordinates

- `Task Forces`
  - Source: `taskforces.json`
  - Fields used: `start_of_day_x`, `start_of_day_y`, `end_of_day_x`,
    `end_of_day_y`, `target_x`, `target_y`, `mission`, `flagship_name`
  - Shows: movement path start -> end and end -> target for non-logistics,
    non-subpatrol task forces

- `Subpatrols`
  - Source: `taskforces.json`
  - Fields used: `mission`, `target_x`, `target_y`
  - Shows: 2-hex patrol circles for `SUBPATROL` task forces

- `Invasions`
  - Sources:
    - `SAVE/combatreport.txt`
    - `threats.json` (`invasion_threat_areas`)
  - Shows: invasion markers (deduplicated by hex center)

- `Threats`
  - Source: `threats.json`
  - Fields used:
    - subtype arrays: `sub_threat_areas`, `surface_threat_areas`,
      `carrier_threat_areas`
    - fallback: `threat_areas[*].threat_types`
    - positions: `position.x`, `position.y`
    - optional radius override: `display_radius_hexes`
  - Shows: subtype threat circles plus general threat-area points

### Logistics layers

- `Base Supply`
  - Source: `bases.json`
  - Fields used: `x`, `y`, `supply`, `supply_needed|supplyNeeded`,
    `fuel`, `fuel_needed|fuelRequested`
  - Shows: supply-state circles (healthy/strained/low)

- `Logistics Taskforces`
  - Source: `taskforces.json`
  - Fields used: `mission`, `end_of_day_x`, `end_of_day_y`,
    `target_x`, `target_y`
  - Shows: logistics route lines for `CARGO` and `TANKER`

### Combat layers

- `Major Actions`
  - Source: `threats.json` (`invasion_threat_areas`)
  - Shows: major combat action markers derived from invasion-threat areas

- `Loss Summaries`
  - Source: `threats.json` (`threat_areas`)
  - Fields used: `position.x`, `position.y`, `threat_score`
  - Shows: severity markers for elevated threat-score areas

### Sea layers

- `HQ Coverage`
  - Source: `ground_units.json`
  - Fields used: `unit_type_name`, `hq_kind`, `end_of_day_x`, `end_of_day_y`
  - Shows: command-radius circles for `naval` and `theater` HQ kinds

- `Unit-HQ Links`
  - Sources: `ships.json`, `bases.json`, `ground_units.json`
  - Fields used: `x`, `y`, `local_fleet_hq_source_unit_id`, `attached_hq_id`
  - Shows: dashed ship-to-HQ linkage lines when resolvable

- `Task Force Vectors`
  - Source: `taskforces.json`
  - Fields used: `mission`, `end_of_day_x`, `end_of_day_y`,
    `target_x`, `target_y`
  - Shows: operational TF vector lines (non-logistics)

- `Minefields`
  - Source: `minefields.json`
  - Fields used: `x`, `y`, `mine_count`, `side`
  - Shows: friendly minefield intensity circles

### Air layers

- `HQ Coverage`
  - Source: `ground_units.json`
  - Fields used: `unit_type_name`, `hq_kind`, `end_of_day_x`, `end_of_day_y`
  - Shows: command-radius circles for `air` and `theater` HQ kinds

- `Air Search`
  - Source: `airgroups.json`
  - Fields used: `x`, `y`, `aircraft_range`, `percent_search`,
    `search_arc_start`, `search_arc_end`
  - Shows: search mission sector wedges

- `Air ASW`
  - Source: `airgroups.json`
  - Fields used: `x`, `y`, `aircraft_range`, `percent_asw`,
    `asw_arc_start`, `asw_arc_end`
  - Shows: ASW mission sector wedges

- `Air Attack Range`
  - Source: `airgroups.json`
  - Fields used: `x`, `y`, `aircraft_range`, allocation percentages
  - Shows: dashed attack-radius circles for strike-capable groups

- `Air HQ Links`
  - Sources: `airgroups.json`, `bases.json`, `ground_units.json`
  - Fields used: `x`, `y`, `assigned_hq_id`, `local_air_hq_source_unit_id`,
    `attached_hq_id`
  - Shows: dashed airgroup-to-HQ linkage lines when resolvable

### Land layers

- `HQ Coverage`
  - Source: `ground_units.json`
  - Fields used: `unit_type_name`, `hq_kind`, `end_of_day_x`, `end_of_day_y`
  - Shows: command-radius circles for `corp`, `army`, and `theater` HQ kinds

- `Area Command`
  - Source: `ground_units.json`
  - Fields used: `area_command`, `end_of_day_x`, `end_of_day_y`
  - Shows: grouped area polygons using convex hull with bbox fallback

- `Ground Unit-HQ Links`
  - Sources: `ground_units.json`, `bases.json`
  - Fields used: `end_of_day_x`, `end_of_day_y`, `effective_hq_id`,
    `attached_hq_id`, `base_chain_hq_id`
  - Shows: unit-to-HQ linkage lines for ground formations

- `Planning`
  - Source: `ground_units.json`
  - Fields used: `end_of_day_x`, `end_of_day_y`, `prep_target_x`,
    `prep_target_y`
  - Shows: dashed planning lines from unit position to prep target

## Overlay Notes

- Several overlays are geometric approximations of pywitpaeui web rendering,
  adapted for direct `QGraphicsScene` drawing.
- Visual parity tuning (styles, thresholds, mission filters, and some
  semantics) should be finalized during runtime verification against known
  saves.

## Map and Hex Calibration

Hex calibration is based on direct measurement from the game-provided
`ART\WPEH00.bmp` reference map rather than visual nudging.

### Calibration approach

1. Load `WPEH00.bmp` as grayscale.
2. Compute horizontal and vertical edge-energy profiles using first
  differences (`abs(diff)`) across pixels.
3. Run lag autocorrelation on each profile over expected spacing ranges:
  - X lag search: 30 to 60 px
  - Y lag search: 25 to 55 px
4. Select the strongest correlation peaks as center-to-center spacing.
5. Cross-check nearby peaks to ensure the result is stable (not a single
  outlier peak).

This method was run with NumPy for reliable and repeatable numeric analysis.

### Final measured spacing

- Horizontal spacing (X): **42 px**
- Vertical spacing (Y): **38 px**

Top peak neighborhoods were consistent around those values:

- X peaks clustered around 41 to 43 px, with 42 px dominant.
- Y peaks clustered around 37 to 39 px, with 38 px dominant.

### Locked implementation values

The runtime constants are locked to the following values in
`app/main_window.py`:

- `HEX_STEP_X = 42.0`
- `HEX_STEP_Y = 38.0`
- `HEX_CENTER_X_1_1 = 24.0`
- `HEX_CENTER_Y_1_1 = 8.0`
- `HEX_ANCHOR_ADJUST_X = 19.0`
- `HEX_ANCHOR_ADJUST_Y = 17.0`
- `SHIFT_EVEN_ROWS_RIGHT = True`

These were spot-checked across multiple locations and are typically within
about 1 to 2 pixels.

Do not adjust these constants by visual nudging. If a future change is needed,
rerun the `WPEH00.bmp` measurement workflow first and then apply a single,
documented recalibration update.

## Project Structure

```text
app/
  main.py            # App startup and CLI parsing
  main_window.py     # Main PyQt5 window and map display shell
  map_assembly.py    # Tile stitching and placeholder generation
  logging_setup.py   # Rich logging configuration
run_ui.bat           # Windows cmd launcher with environment checks
run_ui.ps1           # PowerShell launcher with environment checks
requirements.txt     # Pinned Python dependencies
```

## Logging

Runtime logging uses Python `logging` with `rich.logging.RichHandler` for
readable console output.

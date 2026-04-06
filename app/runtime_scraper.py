"""In-process bridge to legacy pywitpaescraper runtime objects.

This module intentionally keeps overlay/runtime data in-memory and never writes
JSON datasets for GUI consumption.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast
import importlib
import logging
import sys


logger = logging.getLogger(__name__)


def _item_to_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    if is_dataclass(item):
        return cast(dict[str, Any], asdict(cast(Any, item)))
    if hasattr(item, "__dict__"):
        return {
            key: value
            for key, value in vars(item).items()
            if not key.startswith("_")
        }
    return {}


def _extract_taskforces(scraper: Any) -> list[dict[str, Any]]:
    items = getattr(scraper, "active_task_forces", None)
    if not isinstance(items, list):
        return []

    payload_builder = getattr(scraper, "_taskforce_payload", None)
    records: list[dict[str, Any]] = []
    for item in items:
        if callable(payload_builder):
            try:
                payload = payload_builder(item)
                if isinstance(payload, dict):
                    records.append(payload)
                    continue
            except Exception:
                pass
        record = _item_to_dict(item)
        if record:
            records.append(record)
    return records


def _extract_taskforces_from_snapshots(scraper: Any) -> list[dict[str, Any]]:
    """Mirror legacy export_json taskforce logic without writing JSON files."""
    load_snapshot = getattr(scraper, "_load_snapshot", None)
    if not callable(load_snapshot):
        return []

    start_snapshot = load_snapshot(getattr(scraper, "start_of_day_file"), mode=0)
    end_snapshot = load_snapshot(getattr(scraper, "end_of_day_file"), mode=0)
    end_gameday = end_snapshot.get("gameday")

    start_locations_xy = start_snapshot.get("locations_xy", {})
    end_locations_xy = end_snapshot.get("locations_xy", {})

    locations = end_snapshot.get("locations", [])
    ships = end_snapshot.get("ships", [])
    taskgroups = end_snapshot.get("taskgroups", [])
    location_by_id = {int(loc["id"]): loc for loc in locations if isinstance(loc, dict) and "id" in loc}

    pwsdll_module = importlib.import_module("pwsdll")
    task_force_mission = getattr(pwsdll_module, "TaskForceMission")
    nationality = getattr(pwsdll_module, "Nationality")

    nation_allowed = getattr(scraper, "_nation_allowed")
    arrived_by_gameday = getattr(scraper, "_arrived_by_gameday")
    taskforce_id_from_ship_tf = getattr(scraper, "_taskforce_id_from_ship_tf")
    enum_name = getattr(scraper, "_enum_name")

    map_x_min, map_x_max = 1, 232
    map_y_min, map_y_max = 1, 205

    def is_in_map_hex_range(x: int | None, y: int | None) -> bool:
        if x is None or y is None:
            return True
        return map_x_min <= x <= map_x_max and map_y_min <= y <= map_y_max

    ships_by_tf_id: dict[int, list[dict[str, Any]]] = {}
    for ship in ships:
        if not isinstance(ship, dict):
            continue
        ship_nation = int(ship.get("nation", 0))
        if not nation_allowed(ship_nation):
            continue
        if not arrived_by_gameday(int(ship.get("shipDelay", 0)), end_gameday):
            continue
        tf_id = taskforce_id_from_ship_tf(int(ship.get("shipTF", -1)))
        if tf_id is not None:
            ships_by_tf_id.setdefault(int(tf_id), []).append(ship)

    taskforce_records: list[dict[str, Any]] = []
    for tf_id, taskforce in enumerate(taskgroups):
        if not isinstance(taskforce, dict):
            continue
        tf_ships = ships_by_tf_id.get(tf_id, [])
        if not tf_ships:
            continue

        mission_code = int(taskforce.get("tfMission", -1))
        if mission_code == 0:
            continue

        flagship_id = int(taskforce.get("tfFlagship", -1))
        flagship_name = None
        nation_name = None
        start_xy = None
        end_xy = None
        target_xy = None
        target_location_id = None

        if 0 <= flagship_id < len(ships):
            flagship = ships[flagship_id]
            if isinstance(flagship, dict):
                if nation_allowed(int(flagship.get("nation", 0))) and arrived_by_gameday(
                    int(flagship.get("shipDelay", 0)), end_gameday
                ):
                    flagship_name = flagship.get("name") or None
                    nation_name = enum_name(int(flagship.get("nation", 0)), nationality)

                    tf_location_id = int(flagship.get("shipTF", -1))
                    end_xy = end_locations_xy.get(tf_location_id)

                    start_ships = start_snapshot.get("ships", [])
                    if 0 <= flagship_id < len(start_ships):
                        start_flagship = start_ships[flagship_id]
                        if isinstance(start_flagship, dict):
                            start_xy = start_locations_xy.get(int(start_flagship.get("shipTF", -1)))

                    tf_location = location_by_id.get(tf_location_id)
                    if isinstance(tf_location, dict):
                        tx = int(tf_location.get("destX", 0))
                        ty = int(tf_location.get("destY", 0))
                        if tx > 0 and ty > 0:
                            target_xy = (tx, ty)
                            target_location_id = tf_location_id

        if target_xy is None:
            fallback_tf_location_id = tf_id + 14000
            tf_location = location_by_id.get(fallback_tf_location_id)
            if isinstance(tf_location, dict):
                tx = int(tf_location.get("destX", 0))
                ty = int(tf_location.get("destY", 0))
                if tx > 0 and ty > 0:
                    target_xy = (tx, ty)
                    target_location_id = fallback_tf_location_id

        if target_xy is None:
            home_port_id = int(taskforce.get("tfHomePort", -1))
            home_port_xy = end_locations_xy.get(home_port_id)
            if home_port_xy is not None:
                target_xy = home_port_xy
                target_location_id = home_port_id

        if not (
            is_in_map_hex_range(start_xy[0] if start_xy else None, start_xy[1] if start_xy else None)
            and is_in_map_hex_range(end_xy[0] if end_xy else None, end_xy[1] if end_xy else None)
            and is_in_map_hex_range(target_xy[0] if target_xy else None, target_xy[1] if target_xy else None)
        ):
            continue

        taskforce_records.append(
            {
                "record_id": tf_id,
                "mission": enum_name(mission_code, task_force_mission),
                "nation": nation_name,
                "flagship_id": flagship_id,
                "flagship_name": flagship_name,
                "start_of_day_x": start_xy[0] if start_xy else None,
                "start_of_day_y": start_xy[1] if start_xy else None,
                "end_of_day_x": end_xy[0] if end_xy else None,
                "end_of_day_y": end_xy[1] if end_xy else None,
                "target_x": target_xy[0] if target_xy else None,
                "target_y": target_xy[1] if target_xy else None,
                "target_location_id": target_location_id,
            }
        )

    return taskforce_records


def _extract_threats(scraper: Any) -> dict[str, Any]:
    threat_area_payload = getattr(scraper, "_threat_area_payload", None)
    invasion_payload = getattr(scraper, "_invasion_threat_payload", None)

    def _convert(items: Any, builder: Any) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for item in items:
            if callable(builder):
                try:
                    payload = builder(item)
                    if isinstance(payload, dict):
                        out.append(payload)
                        continue
                except Exception:
                    pass
            payload = _item_to_dict(item)
            if payload:
                out.append(payload)
        return out

    return {
        "threat_areas": _convert(getattr(scraper, "active_threat_areas", []), threat_area_payload),
        "sub_threat_areas": _convert(getattr(scraper, "active_sub_threat_areas", []), threat_area_payload),
        "surface_threat_areas": _convert(getattr(scraper, "active_surface_threat_areas", []), threat_area_payload),
        "carrier_threat_areas": _convert(getattr(scraper, "active_carrier_threat_areas", []), threat_area_payload),
        "invasion_threat_areas": _convert(getattr(scraper, "active_invasion_threat_areas", []), invasion_payload),
    }


def _extract_bases(scraper: Any) -> list[dict[str, Any]]:
    """Extract active base records from the scraper for overlay use."""
    items = getattr(scraper, "active_bases", None)
    if not isinstance(items, list):
        return []

    payload_builder = getattr(scraper, "_base_payload", None)
    records: list[dict[str, Any]] = []
    for item in items:
        if callable(payload_builder):
            try:
                payload = payload_builder(item)
                if isinstance(payload, dict):
                    records.append(payload)
                    continue
            except Exception:
                pass
        record = _item_to_dict(item)
        if record:
            records.append(record)
    return records


def _extract_bases_from_snapshots(scraper: Any) -> list[dict[str, Any]]:
    """Extract base records in-memory from the end-of-day snapshot without writing files."""
    load_snapshot = getattr(scraper, "_load_snapshot", None)
    if not callable(load_snapshot):
        return []

    end_snapshot = load_snapshot(getattr(scraper, "end_of_day_file"), mode=0)
    end_gameday = end_snapshot.get("gameday")
    locations = end_snapshot.get("locations", [])

    nation_allowed = getattr(scraper, "_nation_allowed", None)
    arrived_by_gameday = getattr(scraper, "_arrived_by_gameday", None)
    enum_name = getattr(scraper, "_enum_name", None)

    if not callable(nation_allowed) or not callable(arrived_by_gameday) or not callable(enum_name):
        logger.warning("_extract_bases_from_snapshots: required scraper methods are unavailable.")
        return []

    pwsdll_module = importlib.import_module("pwsdll")
    nationality = getattr(pwsdll_module, "Nationality")

    map_x_min, map_x_max = 1, 232
    map_y_min, map_y_max = 1, 205

    base_records: list[dict[str, Any]] = []
    for loc in locations:
        nation_code = int(loc.get("nation", 0))
        if not nation_allowed(nation_code):
            continue
        if not arrived_by_gameday(int(loc.get("arrive", 0)), end_gameday):
            continue
        if str(loc.get("role", "")) != "base":
            continue

        bx = int(loc.get("x", 0))
        by = int(loc.get("y", 0))
        if not (map_x_min <= bx <= map_x_max and map_y_min <= by <= map_y_max):
            continue

        base_records.append(
            {
                "record_id": int(loc.get("id", 0)),
                "name": loc.get("name") or None,
                "nation": enum_name(nation_code, nationality),
                "x": bx,
                "y": by,
                "port": int(loc.get("port", 0)),
                "airfield": int(loc.get("airfield", 0)),
                "supply": int(loc.get("supply", 0)),
                "fuel": int(loc.get("fuel", 0)),
                "runway_damage": int(loc.get("runwayDmg", 0)),
                "port_damage": int(loc.get("portDmg", 0)),
                "airfield_damage": int(loc.get("airfieldDmg", 0)),
            }
        )

    return base_records


def _extract_hqs_from_snapshots(scraper: Any) -> list[dict[str, Any]]:
    """Extract HQ location records from the end-of-day snapshot without writing files.

    Returns one record per HQ location with its position and hq_kind classification:
      - 'naval'  / 'amphib' → Naval HQ overlay
      - 'air'               → Air HQ overlay
      - 'theater' / 'army' / 'corp' → Ground HQ overlay
    """
    load_snapshot = getattr(scraper, "_load_snapshot", None)
    if not callable(load_snapshot):
        return []

    try:
        end_snapshot = load_snapshot(getattr(scraper, "end_of_day_file"), mode=0)
    except Exception as exc:
        logger.warning("_extract_hqs_from_snapshots: failed to load snapshot: %s", exc)
        return []

    end_gameday = end_snapshot.get("gameday")
    locations = end_snapshot.get("locations", [])

    nation_allowed = getattr(scraper, "_nation_allowed", None)
    arrived_by_gameday = getattr(scraper, "_arrived_by_gameday", None)
    enum_name = getattr(scraper, "_enum_name", None)

    if not callable(nation_allowed) or not callable(arrived_by_gameday) or not callable(enum_name):
        logger.warning("_extract_hqs_from_snapshots: required scraper methods are unavailable.")
        return []

    try:
        pwsdll_module = importlib.import_module("pwsdll")
        nationality = getattr(pwsdll_module, "Nationality")
        decode_hq_kind = getattr(pwsdll_module, "decode_hq_kind")
    except Exception:
        logger.warning("_extract_hqs_from_snapshots: pwsdll module or decode_hq_kind unavailable.")
        return []

    # LocationType.HQ == 4
    HQ_TYPE = 4
    map_x_min, map_x_max = 1, 232
    map_y_min, map_y_max = 1, 205

    hq_records: list[dict[str, Any]] = []
    for loc in locations:
        if str(loc.get("role", "")) != "ground_unit":
            continue
        if int(loc.get("type", -1)) != HQ_TYPE:
            continue
        nation_code = int(loc.get("nation", 0))
        if not nation_allowed(nation_code):
            continue
        if not arrived_by_gameday(int(loc.get("arrive", 0)), end_gameday):
            continue

        hx = int(loc.get("x", 0))
        hy = int(loc.get("y", 0))
        if not (map_x_min <= hx <= map_x_max and map_y_min <= hy <= map_y_max):
            continue

        try:
            hq_kind = decode_hq_kind(int(loc.get("HQtype", 0)))
        except Exception as exc:
            logger.debug(
                "_extract_hqs_from_snapshots: failed to decode HQtype for loc id=%s: %s",
                loc.get("id"),
                exc,
            )
            continue
        if hq_kind is None:
            continue

        hq_records.append(
            {
                "record_id": int(loc.get("id", 0)),
                "name": loc.get("name") or None,
                "nation": enum_name(nation_code, nationality),
                "x": hx,
                "y": hy,
                "hq_kind": hq_kind,
                "radius": int(loc.get("radius", 0)),
            }
        )

    return hq_records


def _extract_ground_units_from_snapshots(scraper: Any) -> list[dict[str, Any]]:
    """Extract non-HQ ground unit locations from the end-of-day snapshot.

    Returns one record per ground unit with its name, position, and unit type.
    HQ locations (type == 4) are excluded here as they are covered by the HQ overlay.
    """
    load_snapshot = getattr(scraper, "_load_snapshot", None)
    if not callable(load_snapshot):
        return []

    try:
        end_snapshot = load_snapshot(getattr(scraper, "end_of_day_file"), mode=0)
    except Exception as exc:
        logger.warning("_extract_ground_units_from_snapshots: failed to load snapshot: %s", exc)
        return []

    end_gameday = end_snapshot.get("gameday")
    locations = end_snapshot.get("locations", [])

    nation_allowed = getattr(scraper, "_nation_allowed", None)
    arrived_by_gameday = getattr(scraper, "_arrived_by_gameday", None)
    enum_name = getattr(scraper, "_enum_name", None)

    if not callable(nation_allowed) or not callable(arrived_by_gameday) or not callable(enum_name):
        logger.warning("_extract_ground_units_from_snapshots: required scraper methods are unavailable.")
        return []

    pwsdll_module = importlib.import_module("pwsdll")
    nationality = getattr(pwsdll_module, "Nationality")

    HQ_TYPE = 4
    map_x_min, map_x_max = 1, 232
    map_y_min, map_y_max = 1, 205

    ground_unit_records: list[dict[str, Any]] = []
    for loc in locations:
        if str(loc.get("role", "")) != "ground_unit":
            continue
        if int(loc.get("type", -1)) == HQ_TYPE:
            continue
        nation_code = int(loc.get("nation", 0))
        if not nation_allowed(nation_code):
            continue
        if not arrived_by_gameday(int(loc.get("arrive", 0)), end_gameday):
            continue

        gx = int(loc.get("x", 0))
        gy = int(loc.get("y", 0))
        if not (map_x_min <= gx <= map_x_max and map_y_min <= gy <= map_y_max):
            continue

        ground_unit_records.append(
            {
                "record_id": int(loc.get("id", 0)),
                "name": loc.get("name") or None,
                "nation": enum_name(nation_code, nationality),
                "x": gx,
                "y": gy,
                "unit_type": int(loc.get("type", 0)),
            }
        )

    return ground_unit_records


def _extract_turn(scraper: Any) -> dict[str, Any]:
    scenario_name = getattr(scraper, "scenario_name", None) or getattr(scraper, "scenario", None)
    game_date = getattr(scraper, "game_date", None)
    game_turn = getattr(scraper, "game_turn", None)
    return {
        "scenario_name": str(scenario_name) if scenario_name else "-",
        "game_date": str(game_date) if game_date else "-",
        "game_turn": str(game_turn) if game_turn is not None else "-",
    }


def _load_legacy_scraper_class() -> type[Any]:
    vendored_dir = Path(__file__).resolve().parents[1] / "third_party" / "pywitpaescraper"
    if vendored_dir.exists():
        vendored_path = str(vendored_dir)
        if vendored_path not in sys.path:
            sys.path.insert(0, vendored_path)

    module_candidates = [
        "witpae_today",
        "pywitpaescraper.witpae_today",
    ]

    for module_name in module_candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        scraper_cls = getattr(module, "WITPAE_Today", None)
        if scraper_cls is not None:
            logger.info("Using legacy scraper class from module: %s", module_name)
            return scraper_cls

    raise RuntimeError(
        "Legacy scraper module not available. Expected one of: "
        "'witpae_today' or 'pywitpaescraper.witpae_today'."
    )


def scrape_snapshot(game_dir: Path, save_path: Path, side: str) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    """Return in-memory scraper snapshot from wpae000/wpae002 and logs."""
    start_of_day = save_path / "wpae002.pws"
    end_of_day = save_path / "wpae000.pws"

    if not end_of_day.exists():
        raise FileNotFoundError(f"Missing end-of-day file: {end_of_day}")

    scraper_cls = _load_legacy_scraper_class()
    scraper = scraper_cls(game_dir, start_of_day, end_of_day, side)

    load_day = getattr(scraper, "load_day", None)
    if callable(load_day):
        load_day(end_of_day, mode=0)

    load_logs = getattr(scraper, "_load_log_files", None)
    if callable(load_logs):
        load_logs(save_path)

    taskforces = _extract_taskforces(scraper)
    if not taskforces:
        taskforces = _extract_taskforces_from_snapshots(scraper)

    bases = _extract_bases(scraper)
    if not bases:
        bases = _extract_bases_from_snapshots(scraper)
    threats = _extract_threats(scraper)
    hqs = _extract_hqs_from_snapshots(scraper)
    ground_units = _extract_ground_units_from_snapshots(scraper)

    records = {
        "taskforces": taskforces,
        "invasions": threats.get("invasion_threat_areas", []),
        "bases": bases,
        "hqs": hqs,
        "ground_units": ground_units,
    }
    objects = {
        "threats": threats,
        "turn": _extract_turn(scraper),
    }

    logger.info(
        "Scrape snapshot complete: taskforces=%s bases=%s hqs=%s ground_units=%s threats=%s sub_threats=%s invasions=%s",
        len(records.get("taskforces", [])),
        len(records.get("bases", [])),
        len(records.get("hqs", [])),
        len(records.get("ground_units", [])),
        len(threats.get("threat_areas", [])),
        len(threats.get("sub_threat_areas", [])),
        len(threats.get("invasion_threat_areas", [])),
    )
    return records, objects

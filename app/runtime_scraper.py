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

    records = {
        "taskforces": taskforces,
        "invasions": _extract_threats(scraper).get("invasion_threat_areas", []),
    }
    threats = _extract_threats(scraper)
    objects = {
        "threats": threats,
        "turn": _extract_turn(scraper),
    }

    logger.info(
        "Scrape snapshot complete: taskforces=%s threats=%s sub_threats=%s invasions=%s",
        len(records.get("taskforces", [])),
        len(threats.get("threat_areas", [])),
        len(threats.get("sub_threat_areas", [])),
        len(threats.get("invasion_threat_areas", [])),
    )
    return records, objects

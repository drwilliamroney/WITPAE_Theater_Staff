"""Game data scraper — extracts game state via the DLL interface.

This module bridges the raw ctypes structures from ``dll_interface.pwsdll``
and the clean Python dataclasses in ``data.models``.  It is a significant
simplification / adaptation of the ``witpae_today.py`` module from the
``pywitpaescraper`` project.

When the DLLs are not available (non-Windows, 64-bit interpreter, missing
files), ``GameDataScraper`` falls back to loading JSON exports if they exist.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from witpae_theater_staff.data.models import (
    AirGroupRecord,
    BaseRecord,
    GameState,
    GroundUnitRecord,
    ShipRecord,
    TaskForceRecord,
    ThreatRecord,
    TurnInfo,
)

LOGGER = logging.getLogger(__name__)

# Nationality groups used for side filtering
_JAPAN_NATIONS = {1, 2}   # IJARMY, IJNAVY
_ALLIED_NATIONS = {4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}

_NATION_NAMES: dict[int, str] = {
    0: "",
    1: "IJA",
    2: "IJN",
    3: "",
    4: "USN",
    5: "USA",
    6: "USMC",
    7: "AUS",
    8: "NZ",
    9: "UK",
    10: "FR",
    11: "NL",
    12: "CHN",
    13: "SOV",
    14: "IND",
    15: "CW",
    16: "PHL",
    17: "CCP",
    18: "CAN",
}

_TASK_FORCE_MISSION_NAMES: dict[int, str] = {
    1: "Air Combat",
    2: "Surface",
    3: "Bombardment",
    4: "Fast Transport",
    5: "Transport",
    6: "Replenishment",
    7: "Mine Laying",
    8: "Sub Patrol",
    9: "Sub Mine",
    10: "Sub Transport",
    11: "Cargo",
    13: "Air Transport",
    14: "CV Escort",
    15: "Amphibious",
    16: "ASW Combat",
    17: "PT Boat",
    18: "Tanker",
    19: "Minesweeping",
    20: "Landing Craft",
    22: "Support",
    23: "Local Minesweeping",
    25: "Escort",
}


def _decode_cstr(raw: bytes) -> str:
    """Decode a null-terminated C string from bytes, ignoring bad chars."""
    try:
        return raw.split(b"\x00")[0].decode("latin-1").strip()
    except Exception:
        return ""


class GameDataScraper:
    """Extract a complete ``GameState`` from a WITPAE save file pair.

    Parameters
    ----------
    dll_dir:
        Directory containing ``pwsdll.dll`` and ``pwsdll7.dll``.
    start_of_day_file:
        Path to the start-of-day ``.pws`` save file (``wpae002.pws``).
    end_of_day_file:
        Path to the end-of-day ``.pws`` save file (``wpae000.pws``).
    side:
        ``"ALLIED"`` or ``"JAPAN"``.
    """

    def __init__(
        self,
        dll_dir: Path,
        start_of_day_file: Path,
        end_of_day_file: Path,
        side: str,
    ) -> None:
        self._dll_dir = Path(dll_dir)
        self._sod_file = Path(start_of_day_file)
        self._eod_file = Path(end_of_day_file)
        self._side = side.upper()
        self._pws: Any = None  # PWSDll instance, None if unavailable

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> GameState:
        """Load and return the complete game state.

        Tries the DLL path first; if the DLLs are unavailable, falls back to
        looking for JSON exports in the save directory.
        """
        try:
            return self._load_from_dlls()
        except Exception as exc:
            LOGGER.warning("DLL load failed (%s); trying JSON fallback.", exc)
            return self._load_from_json()

    def export_json(self, output_dir: Path) -> None:
        """Load game state and write JSON export files to *output_dir*."""
        state = self.load()
        output_dir.mkdir(parents=True, exist_ok=True)
        import dataclasses

        def _write(name: str, records: list) -> None:
            path = output_dir / name
            with path.open("w", encoding="utf-8") as fh:
                json.dump([dataclasses.asdict(r) for r in records], fh, indent=2, ensure_ascii=False)
            LOGGER.info("Wrote %d records → %s", len(records), path)

        _write("ships.json", state.ships)
        _write("airgroups.json", state.air_groups)
        _write("ground_units.json", state.ground_units)
        _write("bases.json", state.bases)
        _write("taskforces.json", state.task_forces)

        with (output_dir / "turn.json").open("w", encoding="utf-8") as fh:
            import dataclasses
            json.dump(dataclasses.asdict(state.turn_info), fh, indent=2)

    # ------------------------------------------------------------------
    # DLL loading path
    # ------------------------------------------------------------------

    def _load_from_dlls(self) -> GameState:
        """Extract game state directly from the 32-bit DLLs."""
        from witpae_theater_staff.dll_interface.pwsdll import (
            DllNotAvailableError,
            PWSDll,
            Nationality,
            TaskForceMission,
            LocationType,
            decode_hq_kind,
            ship_class_type_to_name,
            aircraft_type_to_name,
        )

        if self._pws is None:
            self._pws = PWSDll(self._dll_dir)

        pws = self._pws
        eod = self._eod_file
        sod = self._sod_file

        state = GameState()

        # ── turn info ─────────────────────────────────────────────────
        scen = pws.get_scenario_info(eod)
        hdr = pws.get_header(eod)
        state.turn_info = TurnInfo(
            game_turn=scen.gameturn,
            game_date=_decode_cstr(hdr.gameDate),
            scenario=_decode_cstr(scen.scenario),
            japan_vp=scen.japanVP,
            allied_vp=scen.alliedVP,
            side=self._side,
        )

        side_nations = _JAPAN_NATIONS if self._side == "JAPAN" else _ALLIED_NATIONS

        # ── ship classes (lookup table) ────────────────────────────────
        sc_info = pws.get_ship_classes(eod)
        sc_types: dict[int, tuple[str, str, int, int, int, int, int]] = {}
        for i, sc in enumerate(sc_info.shipclass):
            name = _decode_cstr(sc.scName)
            if not name:
                break
            sc_types[i] = (
                name,
                ship_class_type_to_name(sc.scType),
                sc.scTonnage,
                sc.scAircraftCapacity,
                sc.scTroopCapacity,
                sc.scCargoCapacity,
                sc.scLiquidCapacity,
            )

        # ── aircraft types (lookup table) ──────────────────────────────
        ac_info = pws.get_aircraft(eod)
        ac_types: dict[int, tuple[str, str, int]] = {}
        for i, ac in enumerate(ac_info.aircraft):
            name = _decode_cstr(ac.acName)
            if not name:
                break
            ac_types[i] = (name, aircraft_type_to_name(ac.acType), ac.acRange)

        # ── leaders (lookup table) ─────────────────────────────────────
        ld_info = pws.get_leaders(eod)
        leaders: dict[int, tuple[str, str]] = {}
        for i, ld in enumerate(ld_info.leader):
            name = _decode_cstr(ld.ldName)
            if name:
                from witpae_theater_staff.dll_interface.pwsdll import rank_to_name
                leaders[i] = (name, rank_to_name(ld.ldRank))

        # ── locations → bases ──────────────────────────────────────────
        loc_info = pws.get_locations(eod)
        loc_names: dict[int, str] = {}
        for i, loc in enumerate(loc_info.location):
            name = _decode_cstr(loc.locName)
            if not name:
                break
            loc_names[i] = name
            if loc.locType in (1, 5):  # BASE or AF
                if loc.locNation in side_nations or loc.locNation == 0:
                    base = BaseRecord(
                        record_id=i,
                        name=name,
                        nation=_NATION_NAMES.get(loc.locNation, ""),
                        x=loc.locX if loc.locX else None,
                        y=loc.locY if loc.locY else None,
                        port=loc.locPort,
                        airfield=loc.locAirfield,
                        ship_repair_points=loc.locShipRepairPts,
                        supply=loc.locSupply,
                        resources=loc.locResources,
                        fuel=loc.locFuel,
                        port_damage=loc.locPortDamage,
                        airfield_damage=loc.locAirfieldDamage,
                        runway_damage=loc.locRunwayDamage,
                        hq_kind=decode_hq_kind(loc.HQtype),
                    )
                    state.bases.append(base)

        # ── ships ──────────────────────────────────────────────────────
        sh_info = pws.get_ships(eod)
        for i, sh in enumerate(sh_info.ship):
            name = _decode_cstr(sh.shipName)
            if not name:
                break
            if sh.shipNation not in side_nations:
                continue
            sc = sc_types.get(sh.shipClass, ("", "", 0, 0, 0, 0, 0))
            ld_name, ld_rank = leaders.get(sh.shipLeader, (None, None)) if sh.shipLeader else (None, None)
            base_name = loc_names.get(sh.shipBase)
            record = ShipRecord(
                record_id=i,
                name=name,
                nation=_NATION_NAMES.get(sh.shipNation, ""),
                ship_class_name=sc[0],
                ship_class_type_name=sc[1],
                tonnage=sc[2],
                aircraft_capacity=sc[3],
                troop_capacity=sc[4],
                cargo_capacity=sc[5],
                liquid_capacity=sc[6],
                damage=sh.shipDamage,
                endurance=sh.shipEndurance,
                endurance_per_day=sh.shipEndurancePerDay,
                task_force_id=sh.shipTaskForce if sh.shipTaskForce else None,
                base_id=sh.shipBase if sh.shipBase else None,
                base_name=base_name,
                leader_id=sh.shipLeader if sh.shipLeader else None,
                leader_name=ld_name,
                leader_rank=ld_rank,
            )
            state.ships.append(record)

        # ── air groups ─────────────────────────────────────────────────
        ag_info = pws.get_air_groups(eod)
        sod_ag_info = pws.get_air_groups(sod)
        for i, ag in enumerate(ag_info.airgroup):
            name = _decode_cstr(ag.agName)
            if not name:
                break
            if ag.agNation not in side_nations:
                continue
            ac = ac_types.get(ag.agAircraft, ("", "", 0))
            ld_name, ld_rank = leaders.get(ag.agLeader, (None, None)) if ag.agLeader else (None, None)
            base_name = loc_names.get(ag.agBase)
            # location from location record (base record has x/y)
            base_rec = next((b for b in state.bases if b.record_id == ag.agBase), None)
            record = AirGroupRecord(
                record_id=i,
                name=name,
                nation=_NATION_NAMES.get(ag.agNation, ""),
                aircraft_name=ac[0],
                aircraft_type_name=ac[1],
                aircraft_range=ac[2],
                aircraft_active=ag.agActive,
                aircraft_damaged=ag.agDamaged,
                aircraft_max=ag.agMax,
                aircraft_being_repaired=ag.agBeingRepaired,
                leader_id=ag.agLeader if ag.agLeader else None,
                leader_name=ld_name,
                leader_rank=ld_rank,
                hq_id=ag.agHQ if ag.agHQ else None,
                primary_mission_code=ag.agMission,
                secondary_mission_code=ag.agMission2,
                percent_cap=ag.agCapPercent,
                percent_lrcap=ag.agLrCapPercent,
                percent_asw=ag.agAswPercent,
                percent_search=ag.agSearchPercent,
                percent_train=ag.agTrainPercent,
                percent_rest=ag.agRestPercent,
                base_id=ag.agBase if ag.agBase else None,
                base_name=base_name,
                x=base_rec.x if base_rec else None,
                y=base_rec.y if base_rec else None,
            )
            state.air_groups.append(record)

        # ── ground units (from location records of ground-unit type) ───
        from witpae_theater_staff.dll_interface.pwsdll import (
            is_ground_unit_location_type,
            location_type_to_name,
        )
        sod_loc_info = pws.get_locations(sod)
        for i, loc in enumerate(loc_info.location):
            name = _decode_cstr(loc.locName)
            if not name:
                break
            if not is_ground_unit_location_type(loc.locType):
                continue
            if loc.locNation not in side_nations:
                continue
            sod_loc = sod_loc_info.location[i] if i < len(sod_loc_info.location) else None
            record = GroundUnitRecord(
                record_id=i,
                name=name,
                nation=_NATION_NAMES.get(loc.locNation, ""),
                unit_type_name=location_type_to_name(loc.locType),
                start_x=sod_loc.locX if sod_loc else None,
                start_y=sod_loc.locY if sod_loc else None,
                end_x=loc.locX if loc.locX else None,
                end_y=loc.locY if loc.locY else None,
            )
            state.ground_units.append(record)

        # ── task forces ────────────────────────────────────────────────
        tf_info = pws.get_task_groups(eod)
        sod_tf_info = pws.get_task_groups(sod)
        sod_sh_info = pws.get_ships(sod)
        for i, tf in enumerate(tf_info.taskgroup):
            flagship_name = ""
            if tf.tfFlagship and tf.tfFlagship < len(sh_info.ship):
                flagship_name = _decode_cstr(sh_info.ship[tf.tfFlagship].shipName)
            if not flagship_name:
                continue
            mission_code = int.from_bytes(tf.tfMission, "little") if isinstance(tf.tfMission, bytes) else tf.tfMission
            # collect ships in this TF
            ship_ids: list[int] = []
            ship_names: list[str] = []
            for si, sh in enumerate(sh_info.ship):
                sh_name = _decode_cstr(sh.shipName)
                if not sh_name:
                    break
                if sh.shipTaskForce == i:
                    ship_ids.append(si)
                    ship_names.append(sh_name)
            if not ship_ids:
                continue
            # position from flagship's base
            flagship = sh_info.ship[tf.tfFlagship] if tf.tfFlagship < len(sh_info.ship) else None
            base_rec = next((b for b in state.bases if b.record_id == (flagship.shipBase if flagship else 0)), None)
            sod_flagship = sod_sh_info.ship[tf.tfFlagship] if tf.tfFlagship < len(sod_sh_info.ship) else None
            sod_base = next((b for b in state.bases if b.record_id == (sod_flagship.shipBase if sod_flagship else 0)), None)
            record = TaskForceRecord(
                record_id=i,
                flagship_name=flagship_name,
                mission_code=mission_code,
                mission_name=_TASK_FORCE_MISSION_NAMES.get(mission_code, ""),
                home_port_id=tf.tfHomePort if tf.tfHomePort else None,
                start_x=sod_base.x if sod_base else None,
                start_y=sod_base.y if sod_base else None,
                end_x=base_rec.x if base_rec else None,
                end_y=base_rec.y if base_rec else None,
                ship_ids=ship_ids,
                ship_names=ship_names,
            )
            state.task_forces.append(record)

        LOGGER.info(
            "Loaded: %d ships, %d air groups, %d ground units, %d bases, %d task forces",
            len(state.ships), len(state.air_groups), len(state.ground_units),
            len(state.bases), len(state.task_forces),
        )
        return state

    # ------------------------------------------------------------------
    # JSON fallback path
    # ------------------------------------------------------------------

    def _load_from_json(self) -> GameState:
        """Try to load exported JSON files from the save directory."""
        save_dir = self._eod_file.parent
        side_subdir = save_dir / self._side.upper()
        if not side_subdir.is_dir():
            LOGGER.warning("JSON export directory not found: %s", side_subdir)
            return GameState()

        state = GameState()

        def _read(name: str) -> list[dict]:
            p = side_subdir / name
            if not p.exists():
                return []
            with p.open(encoding="utf-8") as fh:
                return json.load(fh)

        # Turn info
        turn_data = _read("turn.json")
        if turn_data:
            t = turn_data if isinstance(turn_data, dict) else {}
            state.turn_info = TurnInfo(
                game_turn=t.get("game_turn", 0),
                game_date=t.get("game_date", ""),
                scenario=t.get("scenario", ""),
                japan_vp=t.get("japan_vp", 0),
                allied_vp=t.get("allied_vp", 0),
                side=self._side,
            )

        for rec in _read("ships.json"):
            state.ships.append(ShipRecord(**{k: v for k, v in rec.items() if k in ShipRecord.__dataclass_fields__}))

        for rec in _read("airgroups.json"):
            state.air_groups.append(AirGroupRecord(**{k: v for k, v in rec.items() if k in AirGroupRecord.__dataclass_fields__}))

        for rec in _read("ground_units.json"):
            state.ground_units.append(GroundUnitRecord(**{k: v for k, v in rec.items() if k in GroundUnitRecord.__dataclass_fields__}))

        for rec in _read("bases.json"):
            state.bases.append(BaseRecord(**{k: v for k, v in rec.items() if k in BaseRecord.__dataclass_fields__}))

        for rec in _read("taskforces.json"):
            state.task_forces.append(TaskForceRecord(**{k: v for k, v in rec.items() if k in TaskForceRecord.__dataclass_fields__}))

        LOGGER.info(
            "Loaded from JSON: %d ships, %d air groups, %d ground units, %d bases, %d task forces",
            len(state.ships), len(state.air_groups), len(state.ground_units),
            len(state.bases), len(state.task_forces),
        )
        return state

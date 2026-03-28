"""Game entity dataclasses.

These are simplified, Python-native representations of the game records
extracted from the DLL interface.  They decouple the UI from the raw ctypes
structures and can be serialised to/from JSON for testing without DLLs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnInfo:
    """Top-level information about the current game turn."""

    game_turn: int = 0
    game_date: str = ""
    scenario: str = ""
    japan_vp: int = 0
    allied_vp: int = 0
    side: str = "ALLIED"  # "ALLIED" or "JAPAN"


@dataclass
class ShipRecord:
    """A single ship extracted from the game save file."""

    record_id: int
    name: str = ""
    nation: str = ""
    ship_class_name: str = ""
    ship_class_type_name: str = ""
    tonnage: int = 0
    aircraft_capacity: int = 0
    troop_capacity: int = 0
    cargo_capacity: int = 0
    liquid_capacity: int = 0
    damage: int = 0
    endurance: int = 0
    endurance_per_day: int = 0
    x: int | None = None
    y: int | None = None
    task_force_id: int | None = None
    base_id: int | None = None
    base_name: str | None = None
    leader_id: int | None = None
    leader_name: str | None = None
    leader_rank: str | None = None
    airgroup_ids: list[int] = field(default_factory=list)
    airgroup_names: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Short display name combining class type and ship name."""
        if self.ship_class_type_name:
            return f"[{self.ship_class_type_name}] {self.name}"
        return self.name

    @property
    def tooltip_text(self) -> str:
        """Concise hover tooltip text."""
        parts = [self.display_name]
        if self.nation:
            parts.append(self.nation)
        if self.damage:
            parts.append(f"Damage: {self.damage}")
        return " | ".join(parts)


@dataclass
class AirGroupRecord:
    """A single air group extracted from the game save file."""

    record_id: int
    name: str = ""
    nation: str = ""
    aircraft_name: str = ""
    aircraft_type_name: str = ""
    aircraft_range: int = 0
    aircraft_active: int = 0
    aircraft_damaged: int = 0
    aircraft_max: int = 0
    aircraft_being_repaired: int = 0
    leader_id: int | None = None
    leader_name: str | None = None
    leader_rank: str | None = None
    hq_id: int | None = None
    hq_name: str | None = None
    primary_mission_code: int = 0
    secondary_mission_code: int = 0
    percent_cap: int = 0
    percent_lrcap: int = 0
    percent_asw: int = 0
    percent_search: int = 0
    percent_train: int = 0
    percent_rest: int = 0
    asw_arc_start: int | None = None
    asw_arc_end: int | None = None
    search_arc_start: int | None = None
    search_arc_end: int | None = None
    x: int | None = None
    y: int | None = None
    base_id: int | None = None
    base_name: str | None = None
    stationed_on_ship_id: int | None = None
    stationed_on_ship_name: str | None = None

    @property
    def tooltip_text(self) -> str:
        """Concise hover tooltip text."""
        parts = [self.name]
        if self.aircraft_name:
            parts.append(self.aircraft_name)
        parts.append(f"{self.aircraft_active}/{self.aircraft_max} a/c")
        return " | ".join(parts)


@dataclass
class GroundUnitRecord:
    """A single ground unit extracted from the game save file."""

    record_id: int
    name: str = ""
    nation: str = ""
    unit_type_name: str = ""
    arrive_day: int = 0
    hq_id: int | None = None
    hq_name: str | None = None
    hq_kind: str | None = None
    base_id: int | None = None
    base_name: str | None = None
    loaded_on_ship_id: int | None = None
    loaded_on_ship_name: str | None = None
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    destination_x: int | None = None
    destination_y: int | None = None

    @property
    def tooltip_text(self) -> str:
        """Concise hover tooltip text."""
        parts = [self.name]
        if self.unit_type_name:
            parts.append(self.unit_type_name)
        if self.nation:
            parts.append(self.nation)
        return " | ".join(parts)


@dataclass
class TaskForceRecord:
    """A single task force extracted from the game save file."""

    record_id: int
    nation: str = ""
    flagship_name: str | None = None
    commander_name: str | None = None
    mission_code: int = 0
    mission_name: str = ""
    home_port_id: int | None = None
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    target_x: int | None = None
    target_y: int | None = None
    ship_ids: list[int] = field(default_factory=list)
    ship_names: list[str] = field(default_factory=list)

    @property
    def tooltip_text(self) -> str:
        """Concise hover tooltip text."""
        parts = []
        if self.flagship_name:
            parts.append(f"TF: {self.flagship_name}")
        else:
            parts.append(f"TF #{self.record_id}")
        parts.append(f"{self.mission_name or 'Unknown'}")
        parts.append(f"{len(self.ship_ids)} ships")
        return " | ".join(parts)


@dataclass
class BaseRecord:
    """A single base location extracted from the game save file."""

    record_id: int
    name: str = ""
    nation: str = ""
    x: int | None = None
    y: int | None = None
    port: int = 0
    airfield: int = 0
    ship_repair_points: int = 0
    supply: int = 0
    resources: int = 0
    fuel: int = 0
    port_damage: int = 0
    airfield_damage: int = 0
    runway_damage: int = 0
    hq_kind: str | None = None
    ship_ids: list[int] = field(default_factory=list)
    ship_names: list[str] = field(default_factory=list)
    air_group_ids: list[int] = field(default_factory=list)
    air_group_names: list[str] = field(default_factory=list)
    ground_unit_ids: list[int] = field(default_factory=list)
    ground_unit_names: list[str] = field(default_factory=list)

    @property
    def supply_health(self) -> str:
        """Classify supply as 'healthy', 'strained', or 'low'."""
        if self.supply >= 50000:
            return "healthy"
        if self.supply >= 10000:
            return "strained"
        return "low"

    @property
    def tooltip_text(self) -> str:
        """Concise hover tooltip text."""
        parts = [self.name]
        if self.port:
            parts.append(f"Port {self.port}")
        if self.airfield:
            parts.append(f"AF {self.airfield}")
        parts.append(f"Supply: {self.supply:,}")
        return " | ".join(parts)


@dataclass
class ThreatRecord:
    """A threat hex record."""

    record_id: int
    x: int
    y: int
    threat_level: int = 0
    threat_type: str = ""


@dataclass
class GameState:
    """Complete game state loaded from one save file pair."""

    turn_info: TurnInfo = field(default_factory=TurnInfo)
    ships: list[ShipRecord] = field(default_factory=list)
    air_groups: list[AirGroupRecord] = field(default_factory=list)
    ground_units: list[GroundUnitRecord] = field(default_factory=list)
    task_forces: list[TaskForceRecord] = field(default_factory=list)
    bases: list[BaseRecord] = field(default_factory=list)
    threats: list[ThreatRecord] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Return True when no data has been loaded."""
        return not any([self.ships, self.air_groups, self.ground_units, self.bases])

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def base_by_id(self, record_id: int) -> BaseRecord | None:
        """Find a base by record ID."""
        return next((b for b in self.bases if b.record_id == record_id), None)

    def ship_by_id(self, record_id: int) -> ShipRecord | None:
        """Find a ship by record ID."""
        return next((s for s in self.ships if s.record_id == record_id), None)

    def task_force_by_id(self, record_id: int) -> TaskForceRecord | None:
        """Find a task force by record ID."""
        return next((tf for tf in self.task_forces if tf.record_id == record_id), None)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation suitable for JSON export."""
        from dataclasses import asdict
        return asdict(self)

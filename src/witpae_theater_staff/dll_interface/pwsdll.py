"""ctypes wrapper for the WITPAE 32-bit game DLLs (pwsdll.dll / pwsdll7.dll).

This module is a direct adaptation of the ``pwsdll.py`` module from the
``pywitpaescraper`` project.  It defines all ctypes structures that mirror the
game's binary record layout and a ``PWSDll`` class that manages loading the two
DLLs and calling their exported functions.

**Platform note**: The DLLs are 32-bit Windows binaries.  This module will
import successfully on any platform but ``PWSDll`` will raise
``DllNotAvailableError`` on non-Windows systems or when a 64-bit interpreter is
detected.  Callers should catch that error and fall back gracefully.
"""

from __future__ import annotations

import ctypes
import logging
import os
import struct
import sys
from enum import IntEnum, IntFlag
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class DllNotAvailableError(RuntimeError):
    """Raised when the game DLLs cannot be loaded."""


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RecType(IntEnum):
    SCENARIO = 1
    HEADER = 38
    AIRGROUP = 20
    PILOT = 22
    AIRCRAFT = 32
    TASKFORCE = 70
    SHIPCLASS = 27
    DEVICE = 31
    LOCATION = 19
    SHIP = 8
    MINES = 30
    LEADER = 21


class Side(IntEnum):
    JAPAN = 0
    ALLIED = 1
    BOTHSIDES = 2


class DeviceType(IntEnum):
    ACCANNON = 0
    GAROCKET = 1
    PGM = 2
    GPBOMB = 3
    APBOMB = 4
    DROPTANK = 5
    RADARDETECT = 6
    JAMMER = 7
    NAVRADAR = 8
    ACRADAR = 9
    SURFRADAR = 10
    AAROCKET = 11
    FLAK = 12
    BALLOON = 13
    FACMACH = 14
    ELINT = 15
    TORPEDO = 16
    DPGUN = 17
    NAVYGUN = 18
    ARMYWEAP = 19
    ASW = 20
    MINE = 21
    AFV = 22
    SQUAD = 23
    ENGR = 24
    VEHICLE = 25
    RESOURCE = 26
    ENGINE = 27


class Nationality(IntEnum):
    NONATIONALITY = 0
    IJARMY = 1
    IJNAVY = 2
    DIVIDER = 3
    USNAVY = 4
    USARMY = 5
    USMARINES = 6
    AUSTRALIAN = 7
    NZ = 8
    BRITISH = 9
    FRENCH = 10
    DUTCH = 11
    CHINESE = 12
    SOVIET = 13
    INDIAN = 14
    CW = 15
    PHIL = 16
    COMCHINESE = 17
    CANADIAN = 18


class Fate(IntEnum):
    ACTIVE = 1
    WIA = 2
    MIA = 3
    KIA = 4
    RES = 0
    TRACOM = 30000


class Rank(IntEnum):
    WO = 0
    LT2 = 1
    LT1 = 2
    CPT = 3
    MAJ = 4
    LTC = 5
    COL = 6
    MGEN = 7
    LGEN = 8
    GEN = 9
    PO2 = 10
    PO1 = 11
    CPO = 12
    WOa = 13
    ENS = 14
    LTJG = 15
    LT = 16
    LCDR = 17
    CDR = 18
    CPTa = 19
    RADM = 20
    VADM = 21
    ADM = 22


class ShipClassType(IntEnum):
    CVB = 1
    CV = 2
    CVL = 3
    CVE = 4
    BB = 5
    BC = 6
    CB = 7
    CA = 8
    CL = 9
    CLAA = 10
    CS = 11
    DD = 12
    DE = 13
    TB = 14
    E = 15
    PG = 16
    PF = 17
    KV = 18
    PC = 19
    PB = 20
    SC = 21
    PT = 22
    MTB = 23
    MGB = 24
    ML = 25
    SS = 26
    SST = 27
    SSX = 28
    AMC = 29
    CM = 30
    CMc = 31
    DM = 32
    DMS = 33
    AM = 34
    AS = 35
    AD = 36
    AV = 37
    AVD = 38
    AVP = 39
    AR = 40
    ARD = 41
    AGP = 42
    AG = 43
    AO = 44
    AE = 45
    AGC = 46
    APA = 47
    AP = 55
    AK = 56
    TK = 60
    LST = 61
    LCI = 62


class AircraftType(IntEnum):
    FI = 0
    FB = 1
    NF = 2
    DB = 3
    LongB = 4
    REC = 5
    MedB = 8
    PBY = 9
    FP = 10
    TBF = 12


class AircraftAttribFlag(IntFlag):
    HEAVY_BOMBER = 0x01
    MEDIUM_BOMBER = 0x02
    ATTACK_BOMBER = 0x04
    CARRIER_CAPABLE = 0x08
    AMPHIBIAN = 0x10
    LIGHT_BOMBER = 0x20
    FLOAT_PLANE = 0x40


class TaskForceMission(IntEnum):
    AIRCOMBAT = 1
    SURFACE = 2
    BOMBARDMENT = 3
    FASTTRANSPORT = 4
    TRANSPORT = 5
    REPLENISHMENT = 6
    MINELAYING = 7
    SUBPATROL = 8
    SUBMINELAYING = 9
    SUBTRANSPORT = 10
    CARGO = 11
    AIRTRANSPORT = 13
    CVESCORT = 14
    AMPHIB = 15
    ASWCOMBAT = 16
    PTBOAT = 17
    TANKER = 18
    MINESWEEPING = 19
    LANDINGCRAFT = 20
    SUPPORT = 22
    LOCALMINESWEEPING = 23
    ESCORT = 25


class LocationType(IntEnum):
    BEACH = 0
    BASE = 1
    AA = 3
    HQ = 4
    AF = 5
    INF = 7
    ARM = 8
    ARTY = 9
    ENGRS = 10
    CD = 11
    TF = 12


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def rank_to_name(rank_value: int) -> str:
    """Convert a rank integer to its string name."""
    try:
        return Rank(rank_value).name
    except ValueError:
        return f"UNKNOWN({rank_value})"


def ship_class_type_to_name(class_type_value: int) -> str:
    """Convert a ship class type integer to its string name."""
    try:
        return ShipClassType(class_type_value).name
    except ValueError:
        return f"UNKNOWN({class_type_value})"


def aircraft_type_to_name(aircraft_type_value: int) -> str:
    """Convert an aircraft type integer to its string name."""
    try:
        return AircraftType(aircraft_type_value).name
    except ValueError:
        return f"UNKNOWN({aircraft_type_value})"


def decode_aircraft_attrib_flags(attrib_value: int) -> dict[str, bool]:
    """Decode aircraft attribute flag byte into a dict of boolean flags."""
    value = int(attrib_value) & 0xFF
    return {
        "heavy_bomber": bool(value & AircraftAttribFlag.HEAVY_BOMBER),
        "medium_bomber": bool(value & AircraftAttribFlag.MEDIUM_BOMBER),
        "light_bomber": bool(value & AircraftAttribFlag.LIGHT_BOMBER),
        "carrier_capable": bool(value & AircraftAttribFlag.CARRIER_CAPABLE),
        "amphibian": bool(value & AircraftAttribFlag.AMPHIBIAN),
        "attack_bomber": bool(value & AircraftAttribFlag.ATTACK_BOMBER),
        "float_plane": bool(value & AircraftAttribFlag.FLOAT_PLANE),
    }


_HQ_KIND_MAP: dict[int, str] = {
    1: "theater",
    2: "army",
    3: "corp",
    4: "air",
    5: "naval",
    6: "amphib",
}


def decode_hq_kind(hq_type_value: int) -> str | None:
    """Decode a PWSLocation.HQtype ushort to a human-readable HQ kind."""
    return _HQ_KIND_MAP.get(hq_type_value)


def location_type_to_name(location_type_value: int) -> str:
    """Convert a location type integer to its string name."""
    try:
        return LocationType(location_type_value).name
    except ValueError:
        return f"UNKNOWN({location_type_value})"


def is_task_force_location_type(location_type_value: int) -> bool:
    """Return True if the location type represents a task force."""
    return location_type_value == LocationType.TF


def is_base_or_beach_location_type(location_type_value: int) -> bool:
    """Return True if the location type represents a base or beach."""
    return location_type_value in (LocationType.BASE, LocationType.AF, LocationType.BEACH)


def is_ground_unit_location_type(location_type_value: int) -> bool:
    """Return True if the location type represents a ground unit."""
    if is_base_or_beach_location_type(location_type_value) or is_task_force_location_type(location_type_value):
        return False
    try:
        LocationType(location_type_value)
    except ValueError:
        return False
    return True


def location_record_role(location_type_value: int) -> str:
    """Classify a location record into dataset role: task_force, base, beach, ground_unit, unknown."""
    if is_task_force_location_type(location_type_value):
        return "task_force"
    if location_type_value in (LocationType.BASE, LocationType.AF):
        return "base"
    if location_type_value == LocationType.BEACH:
        return "beach"
    if is_ground_unit_location_type(location_type_value):
        return "ground_unit"
    return "unknown"


# ---------------------------------------------------------------------------
# ctypes structures (mirror game binary layout)
# ---------------------------------------------------------------------------

class PWSPool(ctypes.Structure):
    _fields_ = [
        ("poolJ", ctypes.c_int),
        ("poolA", ctypes.c_int),
    ]


class PWSTaskGroup(ctypes.Structure):
    _fields_ = [
        ("skip", ctypes.c_char * 4),
        ("tfEndurance", ctypes.c_int),
        ("tfEnduranceReq", ctypes.c_int),
        ("skip2", ctypes.c_char * 32),
        ("tfFlagship", ctypes.c_int),
        ("skip3", ctypes.c_char * 6),
        ("tfHomePort", ctypes.c_ushort),
        ("skip4", ctypes.c_char * 292),
        ("skip4a", ctypes.c_char),
        ("tfMission", ctypes.c_char),
        ("skip5", ctypes.c_char * 3),
        ("tfSpeed", ctypes.c_char),
        ("skip6", ctypes.c_char * 202),
    ]


class PWSTaskGroupInfo(ctypes.Structure):
    _fields_ = [
        ("taskgroup", PWSTaskGroup * 4000),
    ]


class PWSScenInfo(ctypes.Structure):
    _fields_ = [
        ("skip", ctypes.c_char * 30),
        ("gameturn", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 84),
        ("japanVP", ctypes.c_int),
        ("alliedVP", ctypes.c_int),
        ("skip3", ctypes.c_char * 60),
        ("planesBuilt", PWSPool * 1000),
        ("armamentBuilt", PWSPool * 2000),
        ("planeTLoss", ctypes.c_int * 1000),
        ("planeTUsed", PWSPool * 1000),
        ("armamentUsed", PWSPool * 2000),
        ("skip4", ctypes.c_char * 12692),
        ("japanLCULoss", ctypes.c_int),
        ("alliedLCULoss", ctypes.c_int),
        ("japanLCUdayLoss", ctypes.c_int),
        ("alliedLCUdayLoss", ctypes.c_int),
        ("skip5", ctypes.c_char),
        ("gametype", ctypes.c_ubyte),
        ("pbemphase", ctypes.c_ubyte),
        ("password1", ctypes.c_char * 9),
        ("password2", ctypes.c_char * 9),
        ("skip6", ctypes.c_char * 19),
        ("scenario", ctypes.c_char * 25),
    ]


class PWSHeader(ctypes.Structure):
    _fields_ = [
        ("skip", ctypes.c_char * 14),
        ("xSize", ctypes.c_ushort),
        ("ySize", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 4),
        ("gameDate", ctypes.c_char * 12),
        ("skip3", ctypes.c_char * 2),
    ]


class PWSLocation(ctypes.Structure):
    _fields_ = [
        ("locName", ctypes.c_char * 30),
        ("skip", ctypes.c_char * 2),
        ("locType", ctypes.c_ushort),
        ("locNation", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 2),
        ("locX", ctypes.c_ushort),
        ("locY", ctypes.c_ushort),
        ("skip3", ctypes.c_char * 4),
        ("locSupply", ctypes.c_int),
        ("skip4", ctypes.c_char * 4),
        ("locResources", ctypes.c_int),
        ("locFuel", ctypes.c_int),
        ("skip5", ctypes.c_char * 8),
        ("locPort", ctypes.c_ushort),
        ("locPortDamage", ctypes.c_ushort),
        ("locAirfield", ctypes.c_ushort),
        ("locRunwayDamage", ctypes.c_ushort),
        ("locAirfieldDamage", ctypes.c_ushort),
        ("skip6", ctypes.c_char * 14),
        ("locShipRepairPts", ctypes.c_ushort),
        ("skip7", ctypes.c_char * 6),
        ("HQtype", ctypes.c_ushort),
        ("skip8", ctypes.c_char * 62),
    ]


class PWSLocationInfo(ctypes.Structure):
    _fields_ = [
        ("location", PWSLocation * 3000),
    ]


class PWSShip(ctypes.Structure):
    _fields_ = [
        ("shipName", ctypes.c_char * 20),
        ("skip", ctypes.c_char * 2),
        ("shipClass", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 2),
        ("shipNation", ctypes.c_ushort),
        ("skip3", ctypes.c_char * 4),
        ("shipBase", ctypes.c_ushort),
        ("skip4", ctypes.c_char * 2),
        ("shipLeader", ctypes.c_ushort),
        ("skip5", ctypes.c_char * 4),
        ("shipEndurance", ctypes.c_ushort),
        ("shipEndurancePerDay", ctypes.c_ushort),
        ("skip6", ctypes.c_char * 28),
        ("shipTaskForce", ctypes.c_ushort),
        ("skip7", ctypes.c_char * 50),
        ("shipDamage", ctypes.c_ushort),
        ("skip8", ctypes.c_char * 120),
    ]


class PWSShipInfo(ctypes.Structure):
    _fields_ = [
        ("ship", PWSShip * 4000),
    ]


class PWSShipClass(ctypes.Structure):
    _fields_ = [
        ("scName", ctypes.c_char * 20),
        ("skip", ctypes.c_char * 2),
        ("scType", ctypes.c_ushort),
        ("scTonnage", ctypes.c_int),
        ("skip2", ctypes.c_char * 2),
        ("scNation", ctypes.c_ushort),
        ("skip3", ctypes.c_char * 4),
        ("scAircraftCapacity", ctypes.c_ushort),
        ("scTroopCapacity", ctypes.c_ushort),
        ("scCargoCapacity", ctypes.c_ushort),
        ("scLiquidCapacity", ctypes.c_ushort),
        ("skip4", ctypes.c_char * 34),
    ]


class PWSShipClassInfo(ctypes.Structure):
    _fields_ = [
        ("shipclass", PWSShipClass * 500),
    ]


class PWSAirGroup(ctypes.Structure):
    _fields_ = [
        ("agName", ctypes.c_char * 20),
        ("skip", ctypes.c_char * 2),
        ("agAircraft", ctypes.c_ushort),
        ("agActive", ctypes.c_ushort),
        ("agDamaged", ctypes.c_ushort),
        ("agMax", ctypes.c_ushort),
        ("agBeingRepaired", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 2),
        ("agNation", ctypes.c_ushort),
        ("agBase", ctypes.c_ushort),
        ("agLeader", ctypes.c_ushort),
        ("skip3", ctypes.c_char * 4),
        ("agHQ", ctypes.c_ushort),
        ("skip4", ctypes.c_char * 2),
        ("agMission", ctypes.c_ushort),
        ("agMission2", ctypes.c_ushort),
        ("agCapPercent", ctypes.c_ubyte),
        ("agLrCapPercent", ctypes.c_ubyte),
        ("agAswPercent", ctypes.c_ubyte),
        ("agSearchPercent", ctypes.c_ubyte),
        ("agTrainPercent", ctypes.c_ubyte),
        ("agRestPercent", ctypes.c_ubyte),
        ("skip5", ctypes.c_char * 74),
    ]


class PWSAirGroupInfo(ctypes.Structure):
    _fields_ = [
        ("airgroup", PWSAirGroup * 3000),
    ]


class PWSAircraft(ctypes.Structure):
    _fields_ = [
        ("acName", ctypes.c_char * 20),
        ("skip", ctypes.c_char * 2),
        ("acType", ctypes.c_ushort),
        ("acRange", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 4),
        ("acAttrib", ctypes.c_ubyte),
        ("skip3", ctypes.c_char * 33),
    ]


class PWSAircraftInfo(ctypes.Structure):
    _fields_ = [
        ("aircraft", PWSAircraft * 500),
    ]


class PWSLeader(ctypes.Structure):
    _fields_ = [
        ("ldName", ctypes.c_char * 20),
        ("skip", ctypes.c_char * 2),
        ("ldNation", ctypes.c_ushort),
        ("ldRank", ctypes.c_ushort),
        ("ldFate", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 46),
    ]


class PWSLeaderInfo(ctypes.Structure):
    _fields_ = [
        ("leader", PWSLeader * 5000),
    ]


class PWSPilot(ctypes.Structure):
    _fields_ = [
        ("piName", ctypes.c_char * 20),
        ("skip", ctypes.c_char * 2),
        ("piNation", ctypes.c_ushort),
        ("piRank", ctypes.c_ushort),
        ("piFate", ctypes.c_ushort),
        ("piGroup", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 34),
    ]


class PWSPilotInfo(ctypes.Structure):
    _fields_ = [
        ("pilot", PWSPilot * 20000),
    ]


class PWSDevice(ctypes.Structure):
    _fields_ = [
        ("dvName", ctypes.c_char * 20),
        ("skip", ctypes.c_char * 2),
        ("dvType", ctypes.c_ushort),
        ("dvLoad", ctypes.c_ushort),
        ("dvTroopSize", ctypes.c_ushort),
        ("dvCargoSize", ctypes.c_ushort),
        ("skip2", ctypes.c_char * 6),
    ]


class PWSDeviceInfo(ctypes.Structure):
    _fields_ = [
        ("device", PWSDevice * 500),
    ]


class PWSMinefield(ctypes.Structure):
    _fields_ = [
        ("mfX", ctypes.c_ushort),
        ("mfY", ctypes.c_ushort),
        ("mfNation", ctypes.c_ushort),
        ("mfCount", ctypes.c_ushort),
    ]


class PWSMinefieldInfo(ctypes.Structure):
    _fields_ = [
        ("minefield", PWSMinefield * 10000),
    ]


# ---------------------------------------------------------------------------
# PWSDll — main DLL interface class
# ---------------------------------------------------------------------------

class PWSDll:
    """Manage loading the two WITPAE 32-bit DLLs and calling their exported functions.

    Raises ``DllNotAvailableError`` if:
    * the interpreter is not 32-bit, or
    * the DLL files cannot be found / loaded.

    All record-info accessors return ctypes Structure pointers.  The pointer is
    valid only for the lifetime of the loaded save file; re-load before reuse.
    """

    _DLL_NAMES = ("pwsdll.dll", "pwsdll7.dll")

    def __init__(self, dll_dir: Path) -> None:
        """Load DLLs from *dll_dir*.

        Parameters
        ----------
        dll_dir:
            Directory that contains ``pwsdll.dll`` and ``pwsdll7.dll``.
        """
        if struct.calcsize("P") * 8 != 32:
            raise DllNotAvailableError(
                "WITPAE DLLs require a 32-bit Python interpreter; "
                f"this interpreter is {struct.calcsize('P') * 8}-bit."
            )
        if sys.platform != "win32":
            raise DllNotAvailableError(
                "WITPAE DLLs are Windows-only; current platform is "
                f"'{sys.platform}'."
            )

        self._dll_dir = Path(dll_dir)
        self._dll: ctypes.CDLL | None = None
        self._dll7: ctypes.CDLL | None = None
        self._load_dlls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_dlls(self) -> None:
        """Load pwsdll.dll and pwsdll7.dll from ``self._dll_dir``."""
        orig_dir = os.getcwd()
        try:
            # DLLs must be loaded from their own directory so their internal
            # dependencies resolve correctly.
            os.chdir(self._dll_dir)
            dll_path = self._dll_dir / "pwsdll.dll"
            dll7_path = self._dll_dir / "pwsdll7.dll"
            for p in (dll_path, dll7_path):
                if not p.exists():
                    raise DllNotAvailableError(f"DLL not found: {p}")
            self._dll = ctypes.CDLL(str(dll_path))
            self._dll7 = ctypes.CDLL(str(dll7_path))
            LOGGER.info("Loaded DLLs from %s", self._dll_dir)
        except OSError as exc:
            raise DllNotAvailableError(f"Failed to load DLLs: {exc}") from exc
        finally:
            os.chdir(orig_dir)

    def _get_info_ptr(
        self,
        save_file: Path,
        rec_type: RecType,
        info_struct_type: type,
    ) -> ctypes.Structure:
        """Call GetRecInfo for *rec_type* and return a typed pointer."""
        assert self._dll is not None
        fn = self._dll.GetRecInfo
        fn.restype = ctypes.POINTER(info_struct_type)
        result = fn(str(save_file).encode(), ctypes.c_int(int(rec_type)))
        if not result:
            raise RuntimeError(
                f"GetRecInfo returned NULL for rec_type={rec_type!r}, file={save_file}"
            )
        return result.contents

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_scenario_info(self, save_file: Path) -> PWSScenInfo:
        """Return scenario-level info (turn number, VP, …) from *save_file*."""
        return self._get_info_ptr(save_file, RecType.SCENARIO, PWSScenInfo)

    def get_header(self, save_file: Path) -> PWSHeader:
        """Return header record (map size, date) from *save_file*."""
        return self._get_info_ptr(save_file, RecType.HEADER, PWSHeader)

    def get_locations(self, save_file: Path) -> PWSLocationInfo:
        """Return all location records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.LOCATION, PWSLocationInfo)

    def get_ships(self, save_file: Path) -> PWSShipInfo:
        """Return all ship records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.SHIP, PWSShipInfo)

    def get_ship_classes(self, save_file: Path) -> PWSShipClassInfo:
        """Return all ship-class records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.SHIPCLASS, PWSShipClassInfo)

    def get_air_groups(self, save_file: Path) -> PWSAirGroupInfo:
        """Return all air-group records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.AIRGROUP, PWSAirGroupInfo)

    def get_aircraft(self, save_file: Path) -> PWSAircraftInfo:
        """Return all aircraft-type records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.AIRCRAFT, PWSAircraftInfo)

    def get_leaders(self, save_file: Path) -> PWSLeaderInfo:
        """Return all leader records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.LEADER, PWSLeaderInfo)

    def get_pilots(self, save_file: Path) -> PWSPilotInfo:
        """Return all pilot records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.PILOT, PWSPilotInfo)

    def get_devices(self, save_file: Path) -> PWSDeviceInfo:
        """Return all device records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.DEVICE, PWSDeviceInfo)

    def get_task_groups(self, save_file: Path) -> PWSTaskGroupInfo:
        """Return all task-group records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.TASKFORCE, PWSTaskGroupInfo)

    def get_minefields(self, save_file: Path) -> PWSMinefieldInfo:
        """Return all minefield records from *save_file*."""
        return self._get_info_ptr(save_file, RecType.MINES, PWSMinefieldInfo)

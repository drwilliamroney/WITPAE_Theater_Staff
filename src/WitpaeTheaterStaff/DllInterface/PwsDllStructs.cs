using System.Runtime.InteropServices;

namespace WitpaeTheaterStaff.DllInterface;

// ============================================================================
//  C# mirrors of the ctypes structures defined in pywitpaescraper/pwsdll.py
//
//  Layout rules
//  ────────────
//  • [StructLayout(LayoutKind.Sequential)] with no explicit Pack value so
//    the CLR uses natural alignment, which matches Python ctypes default
//    behaviour (verified against actual game save files in pywitpaescraper).
//  • Single-byte game fields (c_char, c_ubyte) → byte.
//  • Multi-byte name/padding arrays (c_char * N) → byte[] with ByValArray.
//  • c_short → short, c_ushort → ushort, c_int → int.
//  • Arrays of primitive types (e.g. c_ushort * 20) → ushort[] with ByValArray.
//  • Name strings are decoded with Encoding.Latin1 / null-terminator trim
//    via PwsDll.CStr().
//
//  Verification note
//  ─────────────────
//  Struct offsets were derived from pywitpaescraper/pwsdll.py (the
//  authoritative source).  If a field reads unexpected data when tested
//  against actual game files, compare the field sequence and sizes against
//  the Python source and adjust accordingly.
// ============================================================================

#pragma warning disable CS0649 // fields assigned via Marshal

/// <summary>Scenario-level information (turn number, victory points, …).</summary>
[StructLayout(LayoutKind.Sequential)]
public struct PWSScenInfo
{
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 30)] public byte[] Skip1;
    public ushort GameTurn;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 84)] public byte[] Skip2;
    public int JapanVP;
    public int AlliedVP;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 60)] public byte[] Skip3;
    // Large pool arrays — we skip over them.
    // PWSPool*1000 (8000) + PWSPool*2000 (16000) + int*1000 (4000) +
    // PWSPool*1000 (8000) + PWSPool*2000 (16000) = 52 000 bytes total.
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 52000)] public byte[] PoolArrays;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 12692)] public byte[] Skip4;
    public int JapanLcuLoss;
    public int AlliedLcuLoss;
    public int JapanLcuDayLoss;
    public int AlliedLcuDayLoss;
    public byte Skip5;
    public byte GameType;
    public byte PbemPhase;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 9)]  public byte[] Password1;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 9)]  public byte[] Password2;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 19)] public byte[] Skip6;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 66)] public byte[] Scenario;
}

/// <summary>
/// Leader record.  Mirrors <c>PWSLeader</c> in <c>pwsdll.py</c>.
/// Total size: 180 bytes.
/// </summary>
[StructLayout(LayoutKind.Sequential)]
public struct PWSLeader
{
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 25)] public byte[] Name;
    public byte Rank;           // rank code byte — see Rank enum in GameEnums
    public byte Leadership;
    public byte Inspiration;
    public byte Naval;
    public byte Air;
    public byte Land;
    public byte Admin;
    public byte Aggression;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 9)] public byte[] Skip1;
    public byte Nation;         // nationality code byte
    public byte Skip2;
    public int  Delay;          // offset 44 — naturally 4-byte aligned
    public byte PolPoints;
    public byte LeaderType;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 130)] public byte[] Skip3;
}

/// <summary>
/// Ship-class record.  Mirrors <c>PWSShipClass</c> in <c>pwsdll.py</c>.
/// Total size: 380 bytes.
/// </summary>
[StructLayout(LayoutKind.Sequential)]
public struct PWSShipClass
{
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 25)] public byte[] Name;
    public byte  ClassType;     // ShipClassType code
    public byte  Nation;
    public byte  Skip1;
    public int   Tonnage;       // offset 28 — naturally 4-byte aligned
    public ushort Fuel;
    public ushort Endurance;
    public byte  MaxSpeed;
    public byte  CruiseSpeed;
    public byte  ManSpeed;
    public byte  Durability;
    public ushort Bitmap;
    public ushort BeltArmor;
    public ushort DeckArmor;
    public ushort TowerArmor;
    public ushort AircraftCapacity;  // "capacity" in Python source
    public ushort TroopCapacity;
    public ushort CargoCapacity;
    public ushort LiquidCapacity;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public ushort[] WepId;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public ushort[] WepNum;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public byte[]   WepFace;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public ushort[] WepAmmo;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public byte[]   WepTurret;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public ushort[] WepArmor;
    public ushort UpgradeId;
    public byte   AvailMonth;
    public byte   AvailYear;
    public byte   UpgradeShipyardSize;
    public byte   Skip2;
    public ushort ClassConvertSet;
    public ushort UpgradeDmg;
    public ushort MinUpgradeDelay;
    public ushort MinConvDelay;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 22)] public byte[] Skip3;
    public byte   SpecialAttribute;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 5)]  public byte[] Skip4;
    public ushort RepairPtsPerDmgPt;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 80)] public byte[] Skip5;
}

/// <summary>
/// Ship record.  Key navigation fields extracted; unknown/unused bytes
/// captured in skip arrays to maintain correct stride.
/// </summary>
[StructLayout(LayoutKind.Sequential)]
public struct PWSShip
{
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public byte[] Name;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip1;
    public ushort ShipClass;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip2;
    public ushort Nation;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]  public byte[] Skip3;
    public ushort BaseId;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip4;
    public ushort LeaderId;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]  public byte[] Skip5;
    public ushort Endurance;
    public ushort EndurancePerDay;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 28)] public byte[] Skip6;
    public ushort TaskForceId;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 50)] public byte[] Skip7;
    public ushort Damage;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 120)] public byte[] Skip8;
}

/// <summary>
/// Location record (bases, ground units, task forces).
/// Key fields extracted; remaining bytes in skip arrays.
/// </summary>
[StructLayout(LayoutKind.Sequential)]
public struct PWSLocation
{
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 30)] public byte[] Name;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip1;
    public ushort LocType;
    public ushort Nation;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip2;
    public ushort X;
    public ushort Y;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]  public byte[] Skip3;
    public int    Supply;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]  public byte[] Skip4;
    public int    Resources;
    public int    Fuel;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]  public byte[] Skip5;
    public ushort Port;
    public ushort PortDamage;
    public ushort Airfield;
    public ushort RunwayDamage;
    public ushort AirfieldDamage;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 14)] public byte[] Skip6;
    public ushort ShipRepairPoints;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 6)]  public byte[] Skip7;
    public ushort HqType;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 62)] public byte[] Skip8;
}

/// <summary>
/// Air-group record.  Key navigation/status fields extracted.
/// Derived from <c>PWSAirGroup</c> in <c>pwsdll.py</c>.
/// </summary>
[StructLayout(LayoutKind.Sequential)]
public struct PWSAirGroup
{
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 26)] public byte[] Name;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]  public byte[] Skip1;
    public short  AircraftTypeId;    // offset 30
    public int    LeaderId;          // offset 32
    public short  HqId;              // offset 36
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip2;
    public ushort BaseId;            // offset 40
    public ushort ReinfBaseId;       // offset 42
    public short  PrimaryMission;    // offset 44
    public short  SecondaryMission;  // offset 46
    public short  TargetId;          // offset 48
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]  public byte[] Skip3;
    public short  FragmentNumber;    // offset 58
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 3)]  public byte[] Skip4;
    public byte   AcPercent;         // offset 63
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 120)] public byte[] Skip5;
    public byte   PilotMorale;       // offset 184
    public byte   PilotExp;          // offset 185
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 6)]  public byte[] Skip6;
    public int    TargetX;           // offset 192
    public int    TargetY;           // offset 196
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]  public byte[] Skip7;
    public byte   AcReady;           // offset 204
    public byte   Skip8;
    public byte   AcMaintained;      // offset 206
    public byte   AcReserve;         // offset 207
    public byte   Skip9;
    public byte   AcDamaged;         // offset 209
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip10;
    public short  AcAlt;             // offset 212
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]  public byte[] Skip11;
    public byte   Nation;            // offset 218
    public byte   Skip12;
    public int    Delay;             // offset 220
    public byte   DelayReinforcement;// offset 224
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 7)]  public byte[] Skip13;
    public short  AcKills;           // offset 232
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip14;
    public short  PilotsAvail;       // offset 236
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 7)]  public byte[] Skip15;
    public byte   MaxPlanes;         // offset 245
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 58)] public byte[] Skip16;
    public short  AcRange;           // offset 304
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip17;
    public short  UpgradeTo;         // offset 308
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 200)] public byte[] SkipRemainder;
}

/// <summary>
/// Aircraft type record.  Mirrors <c>PWSAircraft</c> in <c>pwsdll.py</c>.
/// </summary>
[StructLayout(LayoutKind.Sequential)]
public struct PWSAircraft
{
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 25)] public byte[] Name;
    public byte  AircraftType;   // AircraftType enum code
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip1;
    public ushort MaxAlt;
    public ushort MaxSpeed;
    public ushort CruiseSpeed;
    public ushort ClimbRate;
    public ushort Maneuverability;
    public ushort Endurance;
    public byte   Armor;
    public byte   Durability;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public ushort[] WepId;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public byte[]   Skip2;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public ushort[] WepNum;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)] public byte[]   Skip3;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 10)] public byte[]   WepFace;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 50)] public byte[]   Skip4;
    public ushort MaxLoad;
    public byte   AvailMonth;
    public byte   AvailYear;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip5;
    public ushort BuildRate;
    public ushort Bitmap;
    public ushort Upgrade;
    public ushort Research;
    public int    DayAir;
    public int    DayGround;
    public int    DayFlak;
    public int    DayOps;
    public int    TotAir;
    public int    TotGround;
    public int    TotFlak;
    public int    TotOps;
    public byte   Side;
    public byte   ServiceRating;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 2)]  public byte[] Skip6;
    public byte   Attrib;        // AircraftAttribFlags bit field
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 150)] public byte[] SkipRemainder;
}

/// <summary>
/// Task-group record.  Mirrors <c>PWSTaskGroup</c> in <c>pwsdll.py</c>.
/// </summary>
[StructLayout(LayoutKind.Sequential)]
public struct PWSTaskGroup
{
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]  public byte[] Skip1;
    public int    Endurance;         // offset 4
    public int    EnduranceRequired; // offset 8
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 32)] public byte[] Skip2;
    public int    FlagshipId;        // Flagship unit identifier (see PWSTaskGroup in pwsdll.py)
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 6)]  public byte[] Skip3;
    public ushort HomePortId;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 292)] public byte[] Skip4;
    public byte   Skip4a;
    public byte   Mission;           // TaskForceMission code
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 3)]  public byte[] Skip5;
    public byte   Speed;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 202)] public byte[] Skip6;
}

#pragma warning restore CS0649

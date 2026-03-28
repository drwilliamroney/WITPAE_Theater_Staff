namespace WitpaeTheaterStaff.DllInterface;

/// <summary>Record types passed to <c>GetRecInfo</c> in the game DLL.</summary>
public enum RecType
{
    /// <summary>Scenario-level data (turn number, VP, …).</summary>
    Scenario = 1,
    /// <summary>Ship records.</summary>
    Ship = 8,
    /// <summary>Location records (bases, ground units, task forces).</summary>
    Location = 19,
    /// <summary>Air-group records.</summary>
    AirGroup = 20,
    /// <summary>Leader records.</summary>
    Leader = 21,
    /// <summary>Pilot records.</summary>
    Pilot = 22,
    /// <summary>Ship-class records.</summary>
    ShipClass = 27,
    /// <summary>Mine records.</summary>
    Mines = 30,
    /// <summary>Device (weapon / equipment) records.</summary>
    Device = 31,
    /// <summary>Aircraft-type records.</summary>
    Aircraft = 32,
    /// <summary>Header record (map dimensions, game date).</summary>
    Header = 38,
    /// <summary>Task-group (task-force) records.</summary>
    TaskForce = 70,
}

/// <summary>Player side.</summary>
public enum Side
{
    /// <summary>Imperial Japan (IJA + IJN).</summary>
    Japan = 0,
    /// <summary>Allied forces.</summary>
    Allied = 1,
    /// <summary>Both sides.</summary>
    BothSides = 2,
}

/// <summary>Nationality codes stored in nation fields.</summary>
public enum Nationality
{
    None       = 0,
    IjArmy     = 1,
    IjNavy     = 2,
    Divider    = 3,
    UsNavy     = 4,
    UsArmy     = 5,
    UsMarines  = 6,
    Australian = 7,
    NewZealand = 8,
    British    = 9,
    French     = 10,
    Dutch      = 11,
    Chinese    = 12,
    Soviet     = 13,
    Indian     = 14,
    Commonwealth = 15,
    Philippine = 16,
    CommChinese = 17,
    Canadian   = 18,
}

/// <summary>Location / unit type codes in location records.</summary>
public enum LocationType
{
    Beach  = 0,
    Base   = 1,
    AntiAir = 3,
    Hq     = 4,
    Airfield = 5,
    Infantry = 7,
    Armor  = 8,
    Artillery = 9,
    Engineers = 10,
    CoastDefense = 11,
    TaskForce = 12,
}

/// <summary>Task-force mission codes.</summary>
public enum TaskForceMission
{
    AirCombat        = 1,
    Surface          = 2,
    Bombardment      = 3,
    FastTransport    = 4,
    Transport        = 5,
    Replenishment    = 6,
    MineLaying       = 7,
    SubPatrol        = 8,
    SubMineLaying    = 9,
    SubTransport     = 10,
    Cargo            = 11,
    AirTransport     = 13,
    CvEscort         = 14,
    Amphibious       = 15,
    AswCombat        = 16,
    PtBoat           = 17,
    Tanker           = 18,
    Minesweeping     = 19,
    LandingCraft     = 20,
    Support          = 22,
    LocalMinesweeping = 23,
    Escort           = 25,
}

/// <summary>Ship-class type codes.</summary>
public enum ShipClassType
{
    Cvb = 1, Cv = 2, Cvl = 3, Cve = 4,
    Bb = 5, Bc = 6, Cb = 7, Ca = 8, Cl = 9, Claa = 10,
    Cs = 11, Dd = 12, De = 13, Tb = 14, E = 15,
    Pg = 16, Pf = 17, Kv = 18, Pc = 19, Pb = 20,
    Sc = 21, Pt = 22, Mtb = 23, Mgb = 24, Ml = 25,
    Ss = 26, Sst = 27, Ssx = 28,
    Amc = 29, Cm = 30, CMc = 31, Dm = 32, Dms = 33,
    Am = 34, As = 35, Ad = 36, Av = 37, Avd = 38, Avp = 39,
    Ar = 40, Ard = 41, Agp = 42, Ag = 43, Ao = 44,
    Ae = 45, Agc = 46, Apa = 47,
    Ap = 55, Ak = 56,
    Tk = 60, Lst = 61, Lci = 62,
}

/// <summary>Aircraft type codes.</summary>
public enum AircraftType
{
    Fighter        = 0,
    FighterBomber  = 1,
    NavalFighter   = 2,
    DiveBomber     = 3,
    LongRangeBomber = 4,
    Recon          = 5,
    MediumBomber   = 8,
    FlyingBoat     = 9,
    FloatPlane     = 10,
    TorpedoBomber  = 12,
}

/// <summary>HQ type codes stored in location records.</summary>
public enum HqKind
{
    None    = 0,
    Theater = 1,
    Army    = 2,
    Corp    = 3,
    Air     = 4,
    Naval   = 5,
    Amphib  = 6,
}

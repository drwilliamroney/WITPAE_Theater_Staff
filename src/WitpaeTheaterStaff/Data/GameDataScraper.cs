using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;
using WitpaeTheaterStaff.DllInterface;
using WitpaeTheaterStaff.Data.Models;

namespace WitpaeTheaterStaff.Data;

/// <summary>
/// Extracts a complete <see cref="GameState"/> from a WITPAE save file pair
/// via the 32-bit game DLLs.  Falls back to loading JSON exports when the
/// DLLs are unavailable (development / CI environments).
/// </summary>
public sealed class GameDataScraper : IDisposable
{
    private readonly string _dllDir;
    private readonly string _startOfDayFile;
    private readonly string _endOfDayFile;
    private readonly string _side; // "ALLIED" or "JAPAN"
    private PwsDll? _pws;
    private bool _disposed;

    // Nation codes that belong to each side
    private static readonly HashSet<int> JapanNations  = [1, 2];
    private static readonly HashSet<int> AlliedNations = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18];

    private static readonly Dictionary<int, string> NationNames = new()
    {
        [0]  = "",      [1]  = "IJA",  [2]  = "IJN",  [4]  = "USN",
        [5]  = "USA",   [6]  = "USMC", [7]  = "AUS",  [8]  = "NZ",
        [9]  = "UK",    [10] = "FR",   [11] = "NL",   [12] = "CHN",
        [13] = "SOV",   [14] = "IND",  [15] = "CW",   [16] = "PHL",
        [17] = "CCP",   [18] = "CAN",
    };

    private static readonly Dictionary<int, string> MissionNames = new()
    {
        [1]  = "Air Combat",    [2]  = "Surface",       [3]  = "Bombardment",
        [4]  = "Fast Transport",[5]  = "Transport",     [6]  = "Replenishment",
        [7]  = "Mine Laying",   [8]  = "Sub Patrol",    [9]  = "Sub Mine",
        [10] = "Sub Transport", [11] = "Cargo",         [13] = "Air Transport",
        [14] = "CV Escort",     [15] = "Amphibious",    [16] = "ASW Combat",
        [17] = "PT Boat",       [18] = "Tanker",        [19] = "Minesweeping",
        [20] = "Landing Craft", [22] = "Support",       [23] = "Local Minesweeping",
        [25] = "Escort",
    };

    /// <summary>
    /// Creates a new <see cref="GameDataScraper"/>.
    /// </summary>
    /// <param name="dllDir">Game installation directory containing the DLLs.</param>
    /// <param name="startOfDayFile">Path to <c>wpae002.pws</c>.</param>
    /// <param name="endOfDayFile">Path to <c>wpae000.pws</c>.</param>
    /// <param name="side"><c>"ALLIED"</c> or <c>"JAPAN"</c>.</param>
    public GameDataScraper(
        string dllDir,
        string startOfDayFile,
        string endOfDayFile,
        string side)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(dllDir);
        ArgumentException.ThrowIfNullOrWhiteSpace(startOfDayFile);
        ArgumentException.ThrowIfNullOrWhiteSpace(endOfDayFile);
        ArgumentException.ThrowIfNullOrWhiteSpace(side);

        _dllDir          = dllDir;
        _startOfDayFile  = startOfDayFile;
        _endOfDayFile    = endOfDayFile;
        _side            = side.ToUpperInvariant();
    }

    // ── Public API ────────────────────────────────────────────────────────

    /// <summary>
    /// Loads and returns the complete game state.
    /// Tries the DLL path first; falls back to JSON exports on failure.
    /// </summary>
    public GameState Load()
    {
        try
        {
            return LoadFromDlls();
        }
        catch (DllNotAvailableException ex)
        {
            Trace.TraceWarning($"DLL load failed ({ex.Message}); trying JSON fallback.");
            return LoadFromJson();
        }
        catch (Exception ex)
        {
            Trace.TraceError($"Unexpected error loading game data: {ex}");
            return GameState.Empty;
        }
    }

    // ── DLL loading path ──────────────────────────────────────────────────

    private GameState LoadFromDlls()
    {
        _pws ??= new PwsDll(_dllDir);

        var sideNations = _side == "JAPAN" ? JapanNations : AlliedNations;

        // ── Turn info (pointer-arithmetic reads to avoid marshaling ~65 KB struct) ─
        IntPtr scenPtr = _pws.GetScenInfoPtr(_endOfDayFile);
        int gameTurn = Marshal.ReadInt16(scenPtr + 30);   // gameturn @ offset 30
        int japanVp  = Marshal.ReadInt32(scenPtr + 116);  // japanVP  @ offset 116
        int alliedVp = Marshal.ReadInt32(scenPtr + 120);  // alliedVP @ offset 120
        // scenario name @ offset 64932 (after all pool arrays + skip4 + LCU fields +
        // gametype/password bytes)
        const int ScenarioOffset = 64932;
        byte[] scenBytes = new byte[66];
        Marshal.Copy(scenPtr + ScenarioOffset, scenBytes, 0, 66);
        var turnInfo = new TurnInfo
        {
            GameTurn = gameTurn,
            Scenario = PwsDll.CStr(scenBytes),
            JapanVp  = japanVp,
            AlliedVp = alliedVp,
            Side     = _side,
        };

        // ── Ship classes (lookup table) ───────────────────────────────────
        IntPtr scPtr = _pws.GetShipClassPtr(_endOfDayFile);
        int scStride = Marshal.SizeOf<PWSShipClass>();
        var shipClassLookup = new Dictionary<int, PWSShipClass>();
        for (int i = 0; i < 5000; i++)
        {
            var sc = Marshal.PtrToStructure<PWSShipClass>(scPtr + i * scStride);
            if (sc.Name == null || sc.Name[0] == 0) break;
            shipClassLookup[i] = sc;
        }

        // ── Aircraft types (lookup table) ─────────────────────────────────
        IntPtr acPtr = _pws.GetAircraftPtr(_endOfDayFile);
        int acStride = Marshal.SizeOf<PWSAircraft>();
        var aircraftLookup = new Dictionary<int, PWSAircraft>();
        for (int i = 0; i < 1000; i++)
        {
            var ac = Marshal.PtrToStructure<PWSAircraft>(acPtr + i * acStride);
            if (ac.Name == null || ac.Name[0] == 0) break;
            aircraftLookup[i] = ac;
        }

        // ── Leaders (lookup table) ────────────────────────────────────────
        IntPtr ldPtr = _pws.GetLeaderPtr(_endOfDayFile);
        int ldStride = Marshal.SizeOf<PWSLeader>();
        var leaderLookup = new Dictionary<int, (string Name, string Rank)>();
        for (int i = 0; i < 50000; i++)
        {
            var ld = Marshal.PtrToStructure<PWSLeader>(ldPtr + i * ldStride);
            if (ld.Name == null || ld.Name[0] == 0) break;
            leaderLookup[i] = (PwsDll.CStr(ld.Name), RankName(ld.Rank));
        }

        // ── Locations → bases + ground units ─────────────────────────────
        IntPtr locPtr = _pws.GetLocationPtr(_endOfDayFile);
        IntPtr sodLocPtr = _pws.GetLocationPtr(_startOfDayFile);
        int locStride = Marshal.SizeOf<PWSLocation>();

        var bases       = new List<BaseRecord>();
        var groundUnits = new List<GroundUnitRecord>();
        var locNames    = new Dictionary<int, (string Name, int X, int Y)>();

        for (int i = 0; i < 3000; i++)
        {
            var loc = Marshal.PtrToStructure<PWSLocation>(locPtr + i * locStride);
            if (loc.Name == null || loc.Name[0] == 0) break;

            string name = PwsDll.CStr(loc.Name);
            locNames[i] = (name, loc.X, loc.Y);

            int locType = loc.LocType;
            int nation  = loc.Nation;
            bool sideMatch = sideNations.Contains(nation) || nation == 0;

            if (locType is 1 or 5 && sideMatch) // BASE or AF
            {
                bases.Add(new BaseRecord
                {
                    RecordId         = i,
                    Name             = name,
                    Nation           = NationNames.GetValueOrDefault(nation, ""),
                    X                = loc.X > 0 ? loc.X : null,
                    Y                = loc.Y > 0 ? loc.Y : null,
                    Port             = loc.Port,
                    Airfield         = loc.Airfield,
                    ShipRepairPoints = loc.ShipRepairPoints,
                    Supply           = loc.Supply,
                    Resources        = loc.Resources,
                    Fuel             = loc.Fuel,
                    PortDamage       = loc.PortDamage,
                    AirfieldDamage   = loc.AirfieldDamage,
                    RunwayDamage     = loc.RunwayDamage,
                    HqKind           = HqKindName(loc.HqType),
                });
            }
            else if (IsGroundUnitType(locType) && sideNations.Contains(nation))
            {
                var sodLoc = Marshal.PtrToStructure<PWSLocation>(sodLocPtr + i * locStride);
                groundUnits.Add(new GroundUnitRecord
                {
                    RecordId    = i,
                    Name        = name,
                    Nation      = NationNames.GetValueOrDefault(nation, ""),
                    UnitTypeName = LocationTypeName(locType),
                    HqKind      = locType == 4 ? HqKindName(loc.HqType) : null,
                    StartX      = sodLoc.X > 0 ? sodLoc.X : null,
                    StartY      = sodLoc.Y > 0 ? sodLoc.Y : null,
                    EndX        = loc.X > 0 ? loc.X : null,
                    EndY        = loc.Y > 0 ? loc.Y : null,
                });
            }
        }

        // ── Ships ─────────────────────────────────────────────────────────
        IntPtr shPtr = _pws.GetShipPtr(_endOfDayFile);
        int shStride = Marshal.SizeOf<PWSShip>();
        var ships = new List<ShipRecord>();

        for (int i = 0; i < 4000; i++)
        {
            var sh = Marshal.PtrToStructure<PWSShip>(shPtr + i * shStride);
            if (sh.Name == null || sh.Name[0] == 0) break;
            if (!sideNations.Contains(sh.Nation)) continue;

            shipClassLookup.TryGetValue(sh.ShipClass, out var sc);
            leaderLookup.TryGetValue(sh.LeaderId, out var ld);
            locNames.TryGetValue(sh.BaseId, out var baseLoc);

            ships.Add(new ShipRecord
            {
                RecordId         = i,
                Name             = PwsDll.CStr(sh.Name),
                Nation           = NationNames.GetValueOrDefault(sh.Nation, ""),
                ShipClassName    = sc.Name != null ? PwsDll.CStr(sc.Name) : "",
                ShipClassType    = sc.Name != null ? ((ShipClassType)sc.ClassType).ToString() : "",
                Tonnage          = sc.Name != null ? sc.Tonnage : 0,
                AircraftCapacity = sc.Name != null ? sc.AircraftCapacity : 0,
                TroopCapacity    = sc.Name != null ? sc.TroopCapacity : 0,
                CargoCapacity    = sc.Name != null ? sc.CargoCapacity : 0,
                LiquidCapacity   = sc.Name != null ? sc.LiquidCapacity : 0,
                Damage           = sh.Damage,
                Endurance        = sh.Endurance,
                EndurancePerDay  = sh.EndurancePerDay,
                TaskForceId      = sh.TaskForceId > 0 ? sh.TaskForceId : null,
                BaseId           = sh.BaseId > 0 ? sh.BaseId : null,
                BaseName         = baseLoc.Name,
                LeaderId         = sh.LeaderId > 0 ? sh.LeaderId : null,
                LeaderName       = ld != default ? ld.Name : null,
                X                = baseLoc != default && baseLoc.X > 0 ? baseLoc.X : null,
                Y                = baseLoc != default && baseLoc.Y > 0 ? baseLoc.Y : null,
            });
        }

        // ── Air groups ────────────────────────────────────────────────────
        IntPtr agPtr = _pws.GetAirGroupPtr(_endOfDayFile);
        int agStride = Marshal.SizeOf<PWSAirGroup>();
        var airGroups = new List<AirGroupRecord>();

        for (int i = 0; i < 3000; i++)
        {
            var ag = Marshal.PtrToStructure<PWSAirGroup>(agPtr + i * agStride);
            if (ag.Name == null || ag.Name[0] == 0) break;
            if (!sideNations.Contains(ag.Nation)) continue;

            aircraftLookup.TryGetValue(ag.AircraftTypeId >= 0 ? ag.AircraftTypeId : 0, out var ac);
            locNames.TryGetValue(ag.BaseId, out var baseLoc);

            airGroups.Add(new AirGroupRecord
            {
                RecordId            = i,
                Name                = PwsDll.CStr(ag.Name),
                Nation              = NationNames.GetValueOrDefault(ag.Nation, ""),
                AircraftName        = ac.Name != null ? PwsDll.CStr(ac.Name) : "",
                AircraftTypeName    = ac.Name != null ? ((AircraftType)ac.AircraftType).ToString() : "",
                AircraftRange       = ag.AcRange,
                AcReady             = ag.AcReady,
                AcMaintained        = ag.AcMaintained,
                AcDamaged           = ag.AcDamaged,
                MaxPlanes           = ag.MaxPlanes,
                PilotsAvail         = ag.PilotsAvail,
                PrimaryMissionCode  = ag.PrimaryMission,
                SecondaryMissionCode = ag.SecondaryMission,
                BaseId              = ag.BaseId > 0 ? ag.BaseId : null,
                BaseName            = baseLoc.Name,
                X                   = baseLoc != default && baseLoc.X > 0 ? baseLoc.X : null,
                Y                   = baseLoc != default && baseLoc.Y > 0 ? baseLoc.Y : null,
            });
        }

        // ── Task forces ───────────────────────────────────────────────────
        IntPtr tfPtr = _pws.GetTaskGroupPtr(_endOfDayFile);
        IntPtr sodTfPtr = _pws.GetTaskGroupPtr(_startOfDayFile);
        int tfStride = Marshal.SizeOf<PWSTaskGroup>();
        var taskForces = new List<TaskForceRecord>();

        // Build ship-to-TF lookup
        var shipsByTf = new Dictionary<int, List<(int Id, string Name)>>();
        for (int i = 0; i < ships.Count; i++)
        {
            var s = ships[i];
            if (s.TaskForceId is int tfId)
            {
                if (!shipsByTf.TryGetValue(tfId, out var list))
                    shipsByTf[tfId] = list = [];
                list.Add((s.RecordId, s.Name));
            }
        }

        for (int i = 0; i < 4000; i++)
        {
            var tf = Marshal.PtrToStructure<PWSTaskGroup>(tfPtr + i * tfStride);
            if (tf.FlagshipId <= 0) continue;

            string flagshipName = ships.FirstOrDefault(s => s.RecordId == tf.FlagshipId)?.Name ?? string.Empty;
            if (string.IsNullOrEmpty(flagshipName)) continue;

            shipsByTf.TryGetValue(i, out var tfShips);
            if (tfShips == null || tfShips.Count == 0) continue;

            // Derive position from flagship's base
            var flagship = ships.FirstOrDefault(s => s.RecordId == tf.FlagshipId);
            int? endX = flagship?.X;
            int? endY = flagship?.Y;

            int missionCode = tf.Mission;
            taskForces.Add(new TaskForceRecord
            {
                RecordId    = i,
                FlagshipName = flagshipName,
                MissionCode  = missionCode,
                MissionName  = MissionNames.GetValueOrDefault(missionCode, ""),
                HomePortId   = tf.HomePortId > 0 ? tf.HomePortId : null,
                EndX         = endX,
                EndY         = endY,
                ShipIds      = tfShips.Select(s => s.Id).ToList().AsReadOnly(),
                ShipNames    = tfShips.Select(s => s.Name).ToList().AsReadOnly(),
            });
        }

        Trace.TraceInformation(
            $"Loaded: {ships.Count} ships, {airGroups.Count} air groups, " +
            $"{groundUnits.Count} ground units, {bases.Count} bases, {taskForces.Count} TFs");

        return new GameState
        {
            TurnInfo    = turnInfo,
            Ships       = ships,
            AirGroups   = airGroups,
            GroundUnits = groundUnits,
            TaskForces  = taskForces,
            Bases       = bases,
        };
    }

    // ── JSON fallback ─────────────────────────────────────────────────────

    private GameState LoadFromJson()
    {
        string saveDir = Path.GetDirectoryName(_endOfDayFile) ?? string.Empty;
        string sideDir = Path.Combine(saveDir, _side);
        if (!Directory.Exists(sideDir))
        {
            Trace.TraceWarning($"JSON export directory not found: {sideDir}");
            return GameState.Empty;
        }

        var opts = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };

        T[] Read<T>(string name) where T : class
        {
            string path = Path.Combine(sideDir, name);
            if (!File.Exists(path)) return [];
            try
            {
                using var fs = File.OpenRead(path);
                return JsonSerializer.Deserialize<T[]>(fs, opts) ?? [];
            }
            catch (Exception ex)
            {
                Trace.TraceWarning($"Failed to read {path}: {ex.Message}");
                return [];
            }
        }

        return new GameState
        {
            TurnInfo  = new TurnInfo { Side = _side },
            Ships     = Read<ShipRecord>("ships.json"),
            AirGroups = Read<AirGroupRecord>("airgroups.json"),
            GroundUnits = Read<GroundUnitRecord>("ground_units.json"),
            Bases     = Read<BaseRecord>("bases.json"),
            TaskForces = Read<TaskForceRecord>("taskforces.json"),
        };
    }

    // ── Static helpers ────────────────────────────────────────────────────

    private static string RankName(byte rankByte) => rankByte switch
    {
        0  => "WO",  1  => "2LT", 2  => "1LT", 3  => "CPT",
        4  => "MAJ", 5  => "LTC", 6  => "COL", 7  => "MG",
        8  => "LG",  9  => "GEN", 14 => "ENS", 15 => "LTJG",
        16 => "LT",  17 => "LCDR",18 => "CDR", 19 => "CAPT",
        20 => "RADM",21 => "VADM",22 => "ADM",
        _ => $"Rank{rankByte}",
    };

    private static string? HqKindName(int hqType) => hqType switch
    {
        1 => "theater", 2 => "army", 3 => "corp",
        4 => "air", 5 => "naval", 6 => "amphib",
        _ => null,
    };

    private static string LocationTypeName(int locType) => locType switch
    {
        0  => "Beach",  1 => "Base",  3 => "AA",   4 => "HQ",
        5  => "AF",     7 => "INF",   8 => "ARM",  9 => "ARTY",
        10 => "ENGRS", 11 => "CD",   12 => "TF",
        _ => $"Type{locType}",
    };

    private static bool IsGroundUnitType(int locType) =>
        locType is 3 or 4 or 7 or 8 or 9 or 10 or 11;

    /// <inheritdoc/>
    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _pws?.Dispose();
    }
}

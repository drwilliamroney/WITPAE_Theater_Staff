namespace WitpaeTheaterStaff.Data.Models;

/// <summary>A single air group extracted from the game save file.</summary>
public sealed class AirGroupRecord
{
    /// <summary>Zero-based index in the air-group array.</summary>
    public required int RecordId { get; init; }

    /// <summary>Air-group name.</summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>Nationality string.</summary>
    public string Nation { get; init; } = string.Empty;

    /// <summary>Aircraft type name.</summary>
    public string AircraftName { get; init; } = string.Empty;

    /// <summary>Aircraft type abbreviation (e.g. "FI", "LongB").</summary>
    public string AircraftTypeName { get; init; } = string.Empty;

    /// <summary>Aircraft range in hexes.</summary>
    public int AircraftRange { get; init; }

    /// <summary>Number of aircraft ready for operations.</summary>
    public int AcReady { get; init; }

    /// <summary>Number of aircraft in maintenance.</summary>
    public int AcMaintained { get; init; }

    /// <summary>Number of damaged aircraft.</summary>
    public int AcDamaged { get; init; }

    /// <summary>Maximum aircraft complement.</summary>
    public int MaxPlanes { get; init; }

    /// <summary>Number of available pilots.</summary>
    public int PilotsAvail { get; init; }

    /// <summary>Primary mission code.</summary>
    public int PrimaryMissionCode { get; init; }

    /// <summary>Secondary mission code.</summary>
    public int SecondaryMissionCode { get; init; }

    /// <summary>Zero-based base location index.</summary>
    public int? BaseId { get; init; }

    /// <summary>Name of the base.</summary>
    public string? BaseName { get; init; }

    /// <summary>Hex X coordinate (from base location).</summary>
    public int? X { get; init; }

    /// <summary>Hex Y coordinate (from base location).</summary>
    public int? Y { get; init; }

    /// <summary>Concise tooltip text.</summary>
    public string TooltipText =>
        $"{Name} | {AircraftName} | {AcReady}/{MaxPlanes} a/c";
}

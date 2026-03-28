namespace WitpaeTheaterStaff.Data.Models;

/// <summary>A single ground unit extracted from the game save file.</summary>
public sealed class GroundUnitRecord
{
    /// <summary>Zero-based index in the location array.</summary>
    public required int RecordId { get; init; }

    /// <summary>Unit name.</summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>Nationality string.</summary>
    public string Nation { get; init; } = string.Empty;

    /// <summary>Unit type name (e.g. "INF", "ARM").</summary>
    public string UnitTypeName { get; init; } = string.Empty;

    /// <summary>HQ type string (e.g. "corp", "army"), if applicable.</summary>
    public string? HqKind { get; init; }

    /// <summary>Hex X at start of turn.</summary>
    public int? StartX { get; init; }

    /// <summary>Hex Y at start of turn.</summary>
    public int? StartY { get; init; }

    /// <summary>Hex X at end of turn.</summary>
    public int? EndX { get; init; }

    /// <summary>Hex Y at end of turn.</summary>
    public int? EndY { get; init; }

    /// <summary>Concise tooltip text.</summary>
    public string TooltipText =>
        string.IsNullOrEmpty(UnitTypeName) ? Name : $"{Name} ({UnitTypeName}) | {Nation}";
}

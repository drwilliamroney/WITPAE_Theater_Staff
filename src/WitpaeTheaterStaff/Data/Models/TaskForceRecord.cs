namespace WitpaeTheaterStaff.Data.Models;

/// <summary>A single task force extracted from the game save file.</summary>
public sealed class TaskForceRecord
{
    /// <summary>Zero-based index in the task-group array.</summary>
    public required int RecordId { get; init; }

    /// <summary>Flagship name.</summary>
    public string FlagshipName { get; init; } = string.Empty;

    /// <summary>Mission code.</summary>
    public int MissionCode { get; init; }

    /// <summary>Human-readable mission name.</summary>
    public string MissionName { get; init; } = string.Empty;

    /// <summary>Zero-based home-port location index.</summary>
    public int? HomePortId { get; init; }

    /// <summary>Hex X at start of turn.</summary>
    public int? StartX { get; init; }

    /// <summary>Hex Y at start of turn.</summary>
    public int? StartY { get; init; }

    /// <summary>Hex X at end of turn.</summary>
    public int? EndX { get; init; }

    /// <summary>Hex Y at end of turn.</summary>
    public int? EndY { get; init; }

    /// <summary>Ordered list of zero-based ship indices in this task force.</summary>
    public IReadOnlyList<int> ShipIds { get; init; } = [];

    /// <summary>Ship names for quick display without secondary lookup.</summary>
    public IReadOnlyList<string> ShipNames { get; init; } = [];

    /// <summary>Concise tooltip text.</summary>
    public string TooltipText =>
        $"TF: {FlagshipName} | {MissionName} | {ShipIds.Count} ships";
}

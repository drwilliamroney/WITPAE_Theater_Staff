using System.Collections.Generic;
using System.Linq;

namespace WitpaeTheaterStaff.Data.Models;

/// <summary>
/// Complete game state for one side and one save file pair.
/// Populated by <see cref="GameDataScraper"/>.
/// </summary>
public sealed class GameState
{
    /// <summary>Turn / scenario metadata.</summary>
    public TurnInfo TurnInfo { get; init; } = new();

    /// <summary>All ships visible to the loaded side.</summary>
    public IReadOnlyList<ShipRecord> Ships { get; init; } = [];

    /// <summary>All air groups visible to the loaded side.</summary>
    public IReadOnlyList<AirGroupRecord> AirGroups { get; init; } = [];

    /// <summary>All ground units visible to the loaded side.</summary>
    public IReadOnlyList<GroundUnitRecord> GroundUnits { get; init; } = [];

    /// <summary>All task forces visible to the loaded side.</summary>
    public IReadOnlyList<TaskForceRecord> TaskForces { get; init; } = [];

    /// <summary>All bases visible to the loaded side.</summary>
    public IReadOnlyList<BaseRecord> Bases { get; init; } = [];

    /// <summary>Returns <see langword="true"/> when no data has been loaded.</summary>
    public bool IsEmpty =>
        Ships.Count == 0 && AirGroups.Count == 0 &&
        GroundUnits.Count == 0 && Bases.Count == 0;

    // ── Lookup helpers ────────────────────────────────────────────────────

    /// <summary>Find a base by record ID, or <see langword="null"/>.</summary>
    public BaseRecord? BaseById(int id) =>
        Bases.FirstOrDefault(b => b.RecordId == id);

    /// <summary>Find a ship by record ID, or <see langword="null"/>.</summary>
    public ShipRecord? ShipById(int id) =>
        Ships.FirstOrDefault(s => s.RecordId == id);

    /// <summary>Find a task force by record ID, or <see langword="null"/>.</summary>
    public TaskForceRecord? TaskForceById(int id) =>
        TaskForces.FirstOrDefault(tf => tf.RecordId == id);

    /// <summary>Returns a new empty <see cref="GameState"/>.</summary>
    public static GameState Empty { get; } = new();
}

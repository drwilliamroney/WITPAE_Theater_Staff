using System.Collections.Generic;

namespace WitpaeTheaterStaff.Data.Models;

/// <summary>A single ship extracted from the game save file.</summary>
public sealed class ShipRecord
{
    /// <summary>Zero-based index in the ship array.</summary>
    public required int RecordId { get; init; }

    /// <summary>Ship name.</summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>Nationality string (e.g. "USN", "IJN").</summary>
    public string Nation { get; init; } = string.Empty;

    /// <summary>Ship class name.</summary>
    public string ShipClassName { get; init; } = string.Empty;

    /// <summary>Ship class type abbreviation (e.g. "BB", "CV").</summary>
    public string ShipClassType { get; init; } = string.Empty;

    /// <summary>Tonnage from ship class.</summary>
    public int Tonnage { get; init; }

    /// <summary>Aircraft capacity from ship class.</summary>
    public int AircraftCapacity { get; init; }

    /// <summary>Troop capacity from ship class.</summary>
    public int TroopCapacity { get; init; }

    /// <summary>Cargo capacity from ship class.</summary>
    public int CargoCapacity { get; init; }

    /// <summary>Liquid (fuel) capacity from ship class.</summary>
    public int LiquidCapacity { get; init; }

    /// <summary>Current damage level.</summary>
    public int Damage { get; init; }

    /// <summary>Current endurance.</summary>
    public int Endurance { get; init; }

    /// <summary>Endurance consumed per day at cruise speed.</summary>
    public int EndurancePerDay { get; init; }

    /// <summary>Zero-based task force index, or <see langword="null"/> if not in a TF.</summary>
    public int? TaskForceId { get; init; }

    /// <summary>Zero-based base location index.</summary>
    public int? BaseId { get; init; }

    /// <summary>Name of the base the ship is stationed at.</summary>
    public string? BaseName { get; init; }

    /// <summary>Zero-based leader index, or <see langword="null"/>.</summary>
    public int? LeaderId { get; init; }

    /// <summary>Leader name, or <see langword="null"/>.</summary>
    public string? LeaderName { get; init; }

    /// <summary>Hex X coordinate of current position (derived from base).</summary>
    public int? X { get; init; }

    /// <summary>Hex Y coordinate of current position (derived from base).</summary>
    public int? Y { get; init; }

    /// <summary>Short display label for overlays and lists.</summary>
    public string DisplayLabel =>
        string.IsNullOrEmpty(ShipClassType) ? Name : $"[{ShipClassType}] {Name}";

    /// <summary>Concise tooltip text.</summary>
    public string TooltipText
    {
        get
        {
            var parts = new List<string> { DisplayLabel };
            if (!string.IsNullOrEmpty(Nation)) parts.Add(Nation);
            if (Damage > 0) parts.Add($"Dmg: {Damage}");
            return string.Join(" | ", parts);
        }
    }
}

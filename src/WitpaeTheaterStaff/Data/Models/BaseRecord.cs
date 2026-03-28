namespace WitpaeTheaterStaff.Data.Models;

/// <summary>A single base location extracted from the game save file.</summary>
public sealed class BaseRecord
{
    /// <summary>Zero-based index in the location array.</summary>
    public required int RecordId { get; init; }

    /// <summary>Base name.</summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>Nationality string.</summary>
    public string Nation { get; init; } = string.Empty;

    /// <summary>Hex X coordinate.</summary>
    public int? X { get; init; }

    /// <summary>Hex Y coordinate.</summary>
    public int? Y { get; init; }

    /// <summary>Port level (0 = no port).</summary>
    public int Port { get; init; }

    /// <summary>Airfield level (0 = no airfield).</summary>
    public int Airfield { get; init; }

    /// <summary>Ship repair points available.</summary>
    public int ShipRepairPoints { get; init; }

    /// <summary>Current supply on hand.</summary>
    public int Supply { get; init; }

    /// <summary>Current resources on hand.</summary>
    public int Resources { get; init; }

    /// <summary>Current fuel on hand.</summary>
    public int Fuel { get; init; }

    /// <summary>Port damage level.</summary>
    public int PortDamage { get; init; }

    /// <summary>Airfield damage level.</summary>
    public int AirfieldDamage { get; init; }

    /// <summary>Runway damage level.</summary>
    public int RunwayDamage { get; init; }

    /// <summary>HQ kind if this location is an HQ ("theater", "army", …).</summary>
    public string? HqKind { get; init; }

    /// <summary>
    /// Supply health classification: <c>"healthy"</c>, <c>"strained"</c>,
    /// or <c>"low"</c>.
    /// </summary>
    public string SupplyHealth => Supply switch
    {
        >= 50_000 => "healthy",
        >= 10_000 => "strained",
        _         => "low",
    };

    /// <summary>Concise tooltip text.</summary>
    public string TooltipText
    {
        get
        {
            var parts = new List<string> { Name };
            if (Port > 0)     parts.Add($"Port {Port}");
            if (Airfield > 0) parts.Add($"AF {Airfield}");
            parts.Add($"Supply: {Supply:N0}");
            return string.Join(" | ", parts);
        }
    }
}

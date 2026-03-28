namespace WitpaeTheaterStaff.Data.Models;

/// <summary>Top-level information about the current game turn.</summary>
public sealed class TurnInfo
{
    /// <summary>Game turn number.</summary>
    public int GameTurn { get; init; }

    /// <summary>In-game date string (e.g. "Dec 7, 1941").</summary>
    public string GameDate { get; init; } = string.Empty;

    /// <summary>Scenario name.</summary>
    public string Scenario { get; init; } = string.Empty;

    /// <summary>Current Japanese victory points.</summary>
    public int JapanVp { get; init; }

    /// <summary>Current Allied victory points.</summary>
    public int AlliedVp { get; init; }

    /// <summary>The side currently loaded ("ALLIED" or "JAPAN").</summary>
    public string Side { get; init; } = "ALLIED";
}

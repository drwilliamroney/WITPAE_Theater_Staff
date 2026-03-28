using WitpaeTheaterStaff.Data.Models;
using Xunit;

namespace WitpaeTheaterStaff.Tests;

/// <summary>Unit tests for the game-data model classes.</summary>
public sealed class GameDataModelsTests
{
    // ── BaseRecord.SupplyHealth ───────────────────────────────────────────

    [Theory]
    [InlineData(50_000, "healthy")]
    [InlineData(75_000, "healthy")]
    [InlineData(49_999, "strained")]
    [InlineData(10_000, "strained")]
    [InlineData(9_999,  "low")]
    [InlineData(0,      "low")]
    public void BaseRecord_SupplyHealth_Correct(int supply, string expected)
    {
        var b = new BaseRecord { RecordId = 0, Supply = supply };
        Assert.Equal(expected, b.SupplyHealth);
    }

    // ── BaseRecord.TooltipText ────────────────────────────────────────────

    [Fact]
    public void BaseRecord_TooltipText_IncludesNameAndSupply()
    {
        var b = new BaseRecord
        {
            RecordId = 1,
            Name     = "Pearl Harbor",
            Port     = 6,
            Supply   = 120_000,
        };
        Assert.Contains("Pearl Harbor", b.TooltipText);
        Assert.Contains("120", b.TooltipText);
    }

    // ── ShipRecord.DisplayLabel ───────────────────────────────────────────

    [Fact]
    public void ShipRecord_DisplayLabel_IncludesTypePrefix()
    {
        var s = new ShipRecord
        {
            RecordId      = 0,
            Name          = "USS Enterprise",
            ShipClassType = "CV",
        };
        Assert.StartsWith("[CV]", s.DisplayLabel);
        Assert.Contains("Enterprise", s.DisplayLabel);
    }

    [Fact]
    public void ShipRecord_DisplayLabel_NoTypePrefix_WhenEmpty()
    {
        var s = new ShipRecord { RecordId = 0, Name = "Unknown" };
        Assert.Equal("Unknown", s.DisplayLabel);
    }

    // ── AirGroupRecord.TooltipText ────────────────────────────────────────

    [Fact]
    public void AirGroupRecord_TooltipText_IncludesReadyAndMax()
    {
        var ag = new AirGroupRecord
        {
            RecordId     = 0,
            Name         = "VF-2",
            AircraftName = "F6F Hellcat",
            AcReady      = 18,
            MaxPlanes    = 24,
        };
        Assert.Contains("18", ag.TooltipText);
        Assert.Contains("24", ag.TooltipText);
    }

    // ── TaskForceRecord.TooltipText ───────────────────────────────────────

    [Fact]
    public void TaskForceRecord_TooltipText_IncludesShipCount()
    {
        var tf = new TaskForceRecord
        {
            RecordId    = 0,
            FlagshipName = "USS Hornet",
            MissionName  = "Air Combat",
            ShipIds      = [1, 2, 3, 4, 5],
            ShipNames    = ["A", "B", "C", "D", "E"],
        };
        Assert.Contains("5", tf.TooltipText);
        Assert.Contains("Hornet", tf.TooltipText);
    }

    // ── GameState.IsEmpty ─────────────────────────────────────────────────

    [Fact]
    public void GameState_Empty_IsEmpty()
    {
        Assert.True(GameState.Empty.IsEmpty);
    }

    [Fact]
    public void GameState_WithShips_IsNotEmpty()
    {
        var state = new GameState
        {
            Ships = [new ShipRecord { RecordId = 0, Name = "Test" }],
        };
        Assert.False(state.IsEmpty);
    }

    // ── GameState.BaseById / ShipById ─────────────────────────────────────

    [Fact]
    public void GameState_BaseById_FindsCorrectRecord()
    {
        var b1 = new BaseRecord { RecordId = 10, Name = "Midway" };
        var b2 = new BaseRecord { RecordId = 20, Name = "Truk" };
        var state = new GameState { Bases = [b1, b2] };
        Assert.Same(b2, state.BaseById(20));
        Assert.Null(state.BaseById(99));
    }

    [Fact]
    public void GameState_ShipById_FindsCorrectRecord()
    {
        var s = new ShipRecord { RecordId = 42, Name = "USS Arizona" };
        var state = new GameState { Ships = [s] };
        Assert.Same(s, state.ShipById(42));
        Assert.Null(state.ShipById(0));
    }
}

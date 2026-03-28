using WitpaeTheaterStaff.DllInterface;
using Xunit;

namespace WitpaeTheaterStaff.Tests;

/// <summary>Unit tests for <see cref="GameEnums"/> and related helpers.</summary>
public sealed class GameEnumsTests
{
    // ── RecType values ────────────────────────────────────────────────────

    [Theory]
    [InlineData(RecType.Scenario,  1)]
    [InlineData(RecType.Ship,      8)]
    [InlineData(RecType.Location, 19)]
    [InlineData(RecType.AirGroup, 20)]
    [InlineData(RecType.Leader,   21)]
    [InlineData(RecType.Pilot,    22)]
    [InlineData(RecType.ShipClass,27)]
    [InlineData(RecType.Device,   31)]
    [InlineData(RecType.Aircraft, 32)]
    [InlineData(RecType.Header,   38)]
    [InlineData(RecType.TaskForce,70)]
    public void RecType_HasExpectedIntValue(RecType recType, int expected)
    {
        Assert.Equal(expected, (int)recType);
    }

    // ── Nationality ───────────────────────────────────────────────────────

    [Theory]
    [InlineData(Nationality.IjArmy,     1)]
    [InlineData(Nationality.IjNavy,     2)]
    [InlineData(Nationality.UsNavy,     4)]
    [InlineData(Nationality.UsArmy,     5)]
    [InlineData(Nationality.UsMarines,  6)]
    [InlineData(Nationality.Australian, 7)]
    [InlineData(Nationality.British,    9)]
    [InlineData(Nationality.Canadian,  18)]
    public void Nationality_HasExpectedIntValue(Nationality nat, int expected)
    {
        Assert.Equal(expected, (int)nat);
    }

    // ── LocationType ──────────────────────────────────────────────────────

    [Fact]
    public void LocationType_Base_ValueIs1()
    {
        Assert.Equal(1, (int)LocationType.Base);
    }

    [Fact]
    public void LocationType_TaskForce_ValueIs12()
    {
        Assert.Equal(12, (int)LocationType.TaskForce);
    }

    // ── TaskForceMission ──────────────────────────────────────────────────

    [Theory]
    [InlineData(TaskForceMission.AirCombat,   1)]
    [InlineData(TaskForceMission.Transport,   5)]
    [InlineData(TaskForceMission.Amphibious, 15)]
    [InlineData(TaskForceMission.Escort,     25)]
    public void TaskForceMission_HasExpectedIntValue(TaskForceMission m, int expected)
    {
        Assert.Equal(expected, (int)m);
    }

    // ── PwsDll.CStr ───────────────────────────────────────────────────────

    [Fact]
    public void CStr_NullBytes_ReturnsEmpty()
    {
        Assert.Equal(string.Empty, PwsDll.CStr(null));
    }

    [Fact]
    public void CStr_EmptyArray_ReturnsEmpty()
    {
        Assert.Equal(string.Empty, PwsDll.CStr([]));
    }

    [Fact]
    public void CStr_NullTerminatedBytes_ReturnsCorrectString()
    {
        byte[] bytes = [(byte)'H', (byte)'e', (byte)'l', (byte)'l', (byte)'o', 0, 0, 0];
        Assert.Equal("Hello", PwsDll.CStr(bytes));
    }

    [Fact]
    public void CStr_NoNullTerminator_ReturnsAllBytes()
    {
        byte[] bytes = [(byte)'A', (byte)'B', (byte)'C'];
        Assert.Equal("ABC", PwsDll.CStr(bytes));
    }

    [Fact]
    public void CStr_LeadingAndTrailingSpaces_Trimmed()
    {
        byte[] bytes = [(byte)' ', (byte)'X', (byte)' ', 0];
        Assert.Equal("X", PwsDll.CStr(bytes));
    }

    // ── AppSettings helpers ───────────────────────────────────────────────

    [Theory]
    [InlineData("--side", "japan",  "JAPAN")]
    [InlineData("--side", "allies", "ALLIED")]
    [InlineData("--side", "ALLIED", "ALLIED")]
    [InlineData("--side", "JAPAN",  "JAPAN")]
    public void AppSettings_ApplyArgs_Side(string arg, string value, string expected)
    {
        var s = new WitpaeTheaterStaff.Config.AppSettings();
        s.ApplyArgs([arg, value]);
        Assert.Equal(expected, s.Side);
    }

    [Fact]
    public void AppSettings_ApplyArgs_GamePath()
    {
        var s = new WitpaeTheaterStaff.Config.AppSettings();
        s.ApplyArgs(["--game-path", @"C:\TestGame"]);
        Assert.Equal(@"C:\TestGame", s.GameDir);
    }

    [Fact]
    public void AppSettings_EffectiveSodFile_DerivedFromSaveDir()
    {
        var s = new WitpaeTheaterStaff.Config.AppSettings { SaveDir = @"C:\SAVE" };
        Assert.Equal(@"C:\SAVE\wpae002.pws", s.EffectiveSodFile);
    }

    [Fact]
    public void AppSettings_EffectiveEodFile_DerivedFromSaveDir()
    {
        var s = new WitpaeTheaterStaff.Config.AppSettings { SaveDir = @"C:\SAVE" };
        Assert.Equal(@"C:\SAVE\wpae000.pws", s.EffectiveEodFile);
    }
}

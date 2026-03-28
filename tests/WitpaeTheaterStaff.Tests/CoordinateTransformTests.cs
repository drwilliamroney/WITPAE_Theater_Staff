using WitpaeTheaterStaff.UI;
using Xunit;

namespace WitpaeTheaterStaff.Tests;

/// <summary>Unit tests for <see cref="CoordinateTransform"/>.</summary>
public sealed class CoordinateTransformTests
{
    // ── Constructor validation ────────────────────────────────────────────

    [Theory]
    [InlineData(0,    900)]
    [InlineData(-100, 900)]
    [InlineData(1400, 0)]
    [InlineData(1400, -1)]
    public void Constructor_InvalidDimensions_Throws(double width, double height)
    {
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            new CoordinateTransform(width, height));
    }

    [Theory]
    [InlineData(0.0)]
    [InlineData(-1.0)]
    public void Constructor_InvalidZoom_Throws(double zoom)
    {
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            new CoordinateTransform(1400, 900, zoom));
    }

    // ── HexToPixel ────────────────────────────────────────────────────────

    [Fact]
    public void HexToPixel_Origin_ReturnsZeroZero()
    {
        var t = new CoordinateTransform(1400, 900);
        var (x, y) = t.HexToPixel(1, 1);
        Assert.Equal(0, x, precision: 6);
        Assert.Equal(0, y, precision: 6);
    }

    [Fact]
    public void HexToPixel_MaxHex_ReturnsNearCanvasSize()
    {
        double w = 1400, h = 900;
        var t = new CoordinateTransform(w, h);
        var (x, y) = t.HexToPixel(CoordinateTransform.GameCols, CoordinateTransform.GameRows);
        // Should be exactly one step short of the full canvas size
        double stepX = w / (CoordinateTransform.GameCols - 1);
        double stepY = h / (CoordinateTransform.GameRows - 1);
        Assert.Equal((CoordinateTransform.GameCols - 1) * stepX, x, precision: 6);
        Assert.Equal((CoordinateTransform.GameRows - 1) * stepY, y, precision: 6);
    }

    // ── HexToCenter ───────────────────────────────────────────────────────

    [Fact]
    public void HexToCenter_Origin_ReturnsCenterOfFirstCell()
    {
        double w = 1400, h = 900;
        var t = new CoordinateTransform(w, h);
        var (cx, cy) = t.HexToCenter(1, 1);
        double halfStepX = w / (CoordinateTransform.GameCols - 1) / 2;
        double halfStepY = h / (CoordinateTransform.GameRows - 1) / 2;
        Assert.Equal(halfStepX, cx, precision: 6);
        Assert.Equal(halfStepY, cy, precision: 6);
    }

    [Theory]
    [InlineData(1, 1)]
    [InlineData(116, 103)]
    [InlineData(232, 205)]
    public void HexToCenter_CenterIsInsideCanvas(int hexX, int hexY)
    {
        double w = 1400, h = 900;
        var t = new CoordinateTransform(w, h);
        var (cx, cy) = t.HexToCenter(hexX, hexY);
        Assert.InRange(cx, 0, w);
        Assert.InRange(cy, 0, h);
    }

    // ── Zoom ──────────────────────────────────────────────────────────────

    [Fact]
    public void HexToCenter_WithZoom_ScalesCorrectly()
    {
        double w = 1400, h = 900;
        var t1 = new CoordinateTransform(w, h, 1.0);
        var t2 = new CoordinateTransform(w, h, 2.0);
        var (cx1, cy1) = t1.HexToCenter(50, 50);
        var (cx2, cy2) = t2.HexToCenter(50, 50);
        Assert.Equal(cx1 * 2, cx2, precision: 6);
        Assert.Equal(cy1 * 2, cy2, precision: 6);
    }

    // ── Round-trip ────────────────────────────────────────────────────────

    [Theory]
    [InlineData(1,   1)]
    [InlineData(50,  80)]
    [InlineData(116, 103)]
    [InlineData(232, 205)]
    public void PixelToHex_RoundTrip_ReturnsOriginalHex(int hexX, int hexY)
    {
        var t = new CoordinateTransform(1400, 900);
        var (cx, cy) = t.HexToCenter(hexX, hexY);
        var (rx, ry) = t.PixelToHex(cx, cy);
        Assert.Equal(hexX, rx);
        Assert.Equal(hexY, ry);
    }

    [Theory]
    [InlineData(-100, -100)]
    [InlineData(9999,  9999)]
    public void PixelToHex_OutOfBounds_ClampsToBounds(double px, double py)
    {
        var t = new CoordinateTransform(1400, 900);
        var (hx, hy) = t.PixelToHex(px, py);
        Assert.InRange(hx, 1, CoordinateTransform.GameCols);
        Assert.InRange(hy, 1, CoordinateTransform.GameRows);
    }
}

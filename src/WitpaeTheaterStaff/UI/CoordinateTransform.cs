namespace WitpaeTheaterStaff.UI;

/// <summary>
/// Converts WITPAE game hex coordinates to WPF canvas pixel coordinates.
/// </summary>
/// <remarks>
/// <para>
/// The game uses a 232 × 205 hex grid (1-indexed, so valid X: 1–232, Y: 1–205).
/// This class maps those coordinates to pixel positions on a canvas of any
/// given size, with an optional zoom factor.
/// </para>
/// <para>
/// Two pixel variants are exposed:
/// <list type="bullet">
///   <item><description>
///     <see cref="HexToPixel"/> — top-left corner of the hex cell.
///     Use for region polygon boundary vertices.
///   </description></item>
///   <item><description>
///     <see cref="HexToCenter"/> — visual center of the hex cell.
///     Use for all point-on-hex overlays (ships, air groups, bases, …).
///   </description></item>
/// </list>
/// </para>
/// </remarks>
public sealed class CoordinateTransform
{
    /// <summary>Number of hex columns in the game map (1-indexed).</summary>
    public const int GameCols = 232;

    /// <summary>Number of hex rows in the game map (1-indexed).</summary>
    public const int GameRows = 205;

    private readonly double _stepX;
    private readonly double _stepY;
    private readonly double _canvasWidth;
    private readonly double _canvasHeight;
    private readonly double _zoom;

    /// <summary>
    /// Creates a new transform for a canvas of size
    /// <paramref name="canvasWidth"/> × <paramref name="canvasHeight"/>
    /// at the given <paramref name="zoom"/> level.
    /// </summary>
    /// <param name="canvasWidth">Canvas width in pixels at zoom = 1.0.</param>
    /// <param name="canvasHeight">Canvas height in pixels at zoom = 1.0.</param>
    /// <param name="zoom">Zoom multiplier (default 1.0).</param>
    /// <exception cref="ArgumentOutOfRangeException">
    /// Thrown when <paramref name="canvasWidth"/> or <paramref name="canvasHeight"/>
    /// are non-positive, or <paramref name="zoom"/> is non-positive.
    /// </exception>
    public CoordinateTransform(double canvasWidth, double canvasHeight, double zoom = 1.0)
    {
        if (canvasWidth  <= 0) throw new ArgumentOutOfRangeException(nameof(canvasWidth));
        if (canvasHeight <= 0) throw new ArgumentOutOfRangeException(nameof(canvasHeight));
        if (zoom         <= 0) throw new ArgumentOutOfRangeException(nameof(zoom));

        _canvasWidth = canvasWidth;
        _canvasHeight = canvasHeight;
        _zoom  = zoom;
        _stepX = canvasWidth  / (GameCols - 1);
        _stepY = canvasHeight / (GameRows - 1);
    }

    /// <summary>
    /// Returns the top-left corner pixel of hex (<paramref name="hexX"/>,
    /// <paramref name="hexY"/>) on the unzoomed canvas, then scales by zoom.
    /// </summary>
    public (double X, double Y) HexToPixel(int hexX, int hexY) =>
        ((hexX - 1) * _stepX * _zoom,
         (hexY - 1) * _stepY * _zoom);

    /// <summary>
    /// Returns the center pixel of hex (<paramref name="hexX"/>,
    /// <paramref name="hexY"/>) on the unzoomed canvas, then scales by zoom.
    /// </summary>
    public (double X, double Y) HexToCenter(int hexX, int hexY)
    {
        double x = (hexX - 1) * _stepX * _zoom + _stepX * _zoom / 2.0;
        double y = (hexY - 1) * _stepY * _zoom + _stepY * _zoom / 2.0;
        return (
            Math.Clamp(x, 0, _canvasWidth * _zoom),
            Math.Clamp(y, 0, _canvasHeight * _zoom));
    }

    /// <summary>
    /// Converts a canvas pixel position (after zoom) back to the nearest
    /// game hex coordinate.
    /// </summary>
    public (int HexX, int HexY) PixelToHex(double pixelX, double pixelY)
    {
        int hexX = (int)Math.Round((pixelX - (_stepX * _zoom / 2.0)) / (_stepX * _zoom)) + 1;
        int hexY = (int)Math.Round((pixelY - (_stepY * _zoom / 2.0)) / (_stepY * _zoom)) + 1;
        return (Math.Clamp(hexX, 1, GameCols), Math.Clamp(hexY, 1, GameRows));
    }
}

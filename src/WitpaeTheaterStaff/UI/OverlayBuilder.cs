using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
using WitpaeTheaterStaff.Data.Models;

namespace WitpaeTheaterStaff.UI;

/// <summary>
/// Builds WPF <see cref="UIElement"/> instances for each overlay layer and
/// adds them to named child <see cref="Canvas"/> elements.
/// </summary>
/// <remarks>
/// Call <see cref="Build"/> whenever the game state changes.
/// Each overlay canvas is identified by its <c>Name</c> property:
/// <c>RegionCanvas</c>, <c>TfCanvas</c>, <c>ShipCanvas</c>,
/// <c>BaseCanvas</c>, <c>AirCanvas</c>, <c>LandCanvas</c>,
/// <c>ThreatCanvas</c>.
/// </remarks>
public sealed class OverlayBuilder
{
    private readonly CoordinateTransform _transform;

    /// <summary>Canvas that receives theater region polygons.</summary>
    public Canvas RegionCanvas  { get; } = new() { Tag = "overlay_region" };

    /// <summary>Canvas that receives task-force movement arrows.</summary>
    public Canvas TfCanvas      { get; } = new() { Tag = "overlay_tf" };

    /// <summary>Canvas that receives individual ship dots.</summary>
    public Canvas ShipCanvas    { get; } = new() { Tag = "overlay_ship" };

    /// <summary>Canvas that receives base health circles.</summary>
    public Canvas BaseCanvas    { get; } = new() { Tag = "overlay_base" };

    /// <summary>Canvas that receives air-group dots and arcs.</summary>
    public Canvas AirCanvas     { get; } = new() { Tag = "overlay_air" };

    /// <summary>Canvas that receives ground-unit markers.</summary>
    public Canvas LandCanvas    { get; } = new() { Tag = "overlay_land" };

    /// <summary>Canvas that receives threat heat-map cells.</summary>
    public Canvas ThreatCanvas  { get; } = new() { Tag = "overlay_threat" };

    /// <summary>All overlay canvases in render order (bottom to top).</summary>
    public IReadOnlyList<Canvas> AllCanvases =>
        [RegionCanvas, ThreatCanvas, BaseCanvas, TfCanvas, AirCanvas, LandCanvas, ShipCanvas];

    /// <summary>
    /// Creates a new <see cref="OverlayBuilder"/> using the given coordinate transform.
    /// </summary>
    public OverlayBuilder(CoordinateTransform transform)
    {
        ArgumentNullException.ThrowIfNull(transform);
        _transform = transform;
    }

    /// <summary>
    /// Clears and rebuilds all overlay canvases from <paramref name="state"/>.
    /// </summary>
    public void Build(GameState state)
    {
        ArgumentNullException.ThrowIfNull(state);

        foreach (var c in AllCanvases) c.Children.Clear();

        BuildBases(state.Bases);
        BuildTaskForces(state.TaskForces);
        BuildShips(state.Ships);
        BuildAirGroups(state.AirGroups);
        BuildGroundUnits(state.GroundUnits);
    }

    // ── Per-layer builders ────────────────────────────────────────────────

    private void BuildBases(IReadOnlyList<BaseRecord> bases)
    {
        foreach (var b in bases)
        {
            if (b.X is not int hx || b.Y is not int hy) continue;

            var (cx, cy) = _transform.HexToCenter(hx, hy);
            double r = 6;

            var fill = b.SupplyHealth switch
            {
                "healthy"  => Brushes.LimeGreen,
                "strained" => Brushes.Yellow,
                _          => Brushes.OrangeRed,
            };

            var circle = new Ellipse
            {
                Width           = r * 2,
                Height          = r * 2,
                Fill            = fill,
                Stroke          = Brushes.Black,
                StrokeThickness = 1,
                ToolTip         = b.TooltipText,
                Tag             = b,
            };

            Canvas.SetLeft(circle, cx - r);
            Canvas.SetTop(circle,  cy - r);
            BaseCanvas.Children.Add(circle);
        }
    }

    private void BuildTaskForces(IReadOnlyList<TaskForceRecord> taskForces)
    {
        foreach (var tf in taskForces)
        {
            if (tf.EndX is not int ex || tf.EndY is not int ey) continue;

            var (endCx, endCy) = _transform.HexToCenter(ex, ey);

            // Draw arrow line if start position differs from end
            if (tf.StartX is int sx && tf.StartY is int sy && (sx != ex || sy != ey))
            {
                var (startCx, startCy) = _transform.HexToCenter(sx, sy);
                var line = new Line
                {
                    X1              = startCx,
                    Y1              = startCy,
                    X2              = endCx,
                    Y2              = endCy,
                    Stroke          = Brushes.Cyan,
                    StrokeThickness = 1.5,
                    ToolTip         = tf.TooltipText,
                    Tag             = tf,
                };
                TfCanvas.Children.Add(line);
            }

            // Draw endpoint marker
            const double r = 5;
            var dot = new Ellipse
            {
                Width           = r * 2,
                Height          = r * 2,
                Fill            = Brushes.Cyan,
                Stroke          = Brushes.DarkCyan,
                StrokeThickness = 1,
                ToolTip         = tf.TooltipText,
                Tag             = tf,
            };
            Canvas.SetLeft(dot, endCx - r);
            Canvas.SetTop(dot,  endCy - r);
            TfCanvas.Children.Add(dot);
        }
    }

    private void BuildShips(IReadOnlyList<ShipRecord> ships)
    {
        foreach (var s in ships)
        {
            if (s.X is not int hx || s.Y is not int hy) continue;

            var (cx, cy) = _transform.HexToCenter(hx, hy);
            const double r = 3;

            var dot = new Ellipse
            {
                Width           = r * 2,
                Height          = r * 2,
                Fill            = Brushes.LightSteelBlue,
                Stroke          = Brushes.Navy,
                StrokeThickness = 0.5,
                ToolTip         = s.TooltipText,
                Tag             = s,
            };
            Canvas.SetLeft(dot, cx - r);
            Canvas.SetTop(dot,  cy - r);
            ShipCanvas.Children.Add(dot);
        }
    }

    private void BuildAirGroups(IReadOnlyList<AirGroupRecord> airGroups)
    {
        foreach (var ag in airGroups)
        {
            if (ag.X is not int hx || ag.Y is not int hy) continue;

            var (cx, cy) = _transform.HexToCenter(hx, hy);
            const double r = 4;

            var dot = new Ellipse
            {
                Width           = r * 2,
                Height          = r * 2,
                Fill            = Brushes.Yellow,
                Stroke          = Brushes.DarkGoldenrod,
                StrokeThickness = 1,
                ToolTip         = ag.TooltipText,
                Tag             = ag,
            };
            Canvas.SetLeft(dot, cx - r);
            Canvas.SetTop(dot,  cy - r);
            AirCanvas.Children.Add(dot);
        }
    }

    private void BuildGroundUnits(IReadOnlyList<GroundUnitRecord> groundUnits)
    {
        foreach (var gu in groundUnits)
        {
            if (gu.EndX is not int hx || gu.EndY is not int hy) continue;

            var (cx, cy) = _transform.HexToCenter(hx, hy);
            const double size = 8;

            var rect = new Rectangle
            {
                Width           = size,
                Height          = size,
                Fill            = Brushes.Olive,
                Stroke          = Brushes.DarkOliveGreen,
                StrokeThickness = 1,
                ToolTip         = gu.TooltipText,
                Tag             = gu,
            };
            Canvas.SetLeft(rect, cx - size / 2);
            Canvas.SetTop(rect,  cy - size / 2);
            LandCanvas.Children.Add(rect);
        }
    }
}

using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using WitpaeTheaterStaff.Data.Models;

namespace WitpaeTheaterStaff.UI;

/// <summary>
/// Builds <see cref="ToolTip"/> content for game objects hovered on the map canvas.
/// </summary>
public static class HexTooltip
{
    /// <summary>
    /// Builds a <see cref="ToolTip"/> appropriate for <paramref name="gameObject"/>.
    /// Returns <see langword="null"/> when the object type is not recognised.
    /// </summary>
    public static ToolTip? Build(object? gameObject)
    {
        string? text = gameObject switch
        {
            ShipRecord       s  => s.TooltipText,
            AirGroupRecord   ag => ag.TooltipText,
            GroundUnitRecord gu => gu.TooltipText,
            TaskForceRecord  tf => tf.TooltipText,
            BaseRecord       b  => b.TooltipText,
            _                   => null,
        };

        if (text is null) return null;

        return new ToolTip
        {
            Content = new TextBlock
            {
                Text       = text,
                Padding    = new Thickness(4, 2, 4, 2),
                FontFamily = new System.Windows.Media.FontFamily("Segoe UI"),
                FontSize   = 11,
            },
        };
    }

    /// <summary>
    /// Returns a multi-line detail string for a game object, suitable for
    /// populating the detail panel.
    /// </summary>
    public static IEnumerable<(string Label, string Value)> DetailRows(object? gameObject)
    {
        return gameObject switch
        {
            ShipRecord s => ShipDetail(s),
            AirGroupRecord ag => AirDetail(ag),
            GroundUnitRecord gu => GroundDetail(gu),
            TaskForceRecord tf => TfDetail(tf),
            BaseRecord b => BaseDetail(b),
            _ => [],
        };
    }

    private static IEnumerable<(string, string)> ShipDetail(ShipRecord s)
    {
        yield return ("Name",       s.Name);
        yield return ("Nation",     s.Nation);
        yield return ("Class",      s.ShipClassName);
        yield return ("Type",       s.ShipClassType);
        yield return ("Tonnage",    $"{s.Tonnage:N0}");
        yield return ("Damage",     s.Damage.ToString());
        yield return ("Endurance",  $"{s.Endurance} / {s.EndurancePerDay} per day");
        if (s.LeaderName is not null)
            yield return ("Leader", s.LeaderName);
        if (s.BaseName is not null)
            yield return ("At base", s.BaseName);
    }

    private static IEnumerable<(string, string)> AirDetail(AirGroupRecord ag)
    {
        yield return ("Name",     ag.Name);
        yield return ("Nation",   ag.Nation);
        yield return ("Aircraft", ag.AircraftName);
        yield return ("Type",     ag.AircraftTypeName);
        yield return ("Ready",    ag.AcReady.ToString());
        yield return ("Max",      ag.MaxPlanes.ToString());
        yield return ("Range",    $"{ag.AircraftRange} hexes");
        if (ag.BaseName is not null)
            yield return ("At base", ag.BaseName);
    }

    private static IEnumerable<(string, string)> GroundDetail(GroundUnitRecord gu)
    {
        yield return ("Name",   gu.Name);
        yield return ("Nation", gu.Nation);
        yield return ("Type",   gu.UnitTypeName);
        if (gu.HqKind is not null)
            yield return ("HQ kind", gu.HqKind);
    }

    private static IEnumerable<(string, string)> TfDetail(TaskForceRecord tf)
    {
        yield return ("Flagship", tf.FlagshipName);
        yield return ("Mission",  tf.MissionName);
        yield return ("Ships",    tf.ShipIds.Count.ToString());
        foreach (var name in tf.ShipNames.Take(10))
            yield return ("  •", name);
        if (tf.ShipNames.Count > 10)
            yield return ("  …", $"{tf.ShipNames.Count - 10} more");
    }

    private static IEnumerable<(string, string)> BaseDetail(BaseRecord b)
    {
        yield return ("Name",          b.Name);
        yield return ("Nation",        b.Nation);
        yield return ("Port",          b.Port.ToString());
        yield return ("Airfield",      b.Airfield.ToString());
        yield return ("Supply",        $"{b.Supply:N0}");
        yield return ("Resources",     $"{b.Resources:N0}");
        yield return ("Fuel",          $"{b.Fuel:N0}");
        yield return ("Supply health", b.SupplyHealth);
        if (b.PortDamage > 0)
            yield return ("Port damage", b.PortDamage.ToString());
        if (b.AirfieldDamage > 0)
            yield return ("AF damage",   b.AirfieldDamage.ToString());
    }
}

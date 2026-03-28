using System.Windows.Controls;

namespace WitpaeTheaterStaff.UI;

/// <summary>
/// A right-side detail panel that displays field/value rows for the
/// currently selected or hovered game object.
/// </summary>
public partial class DetailPanel : UserControl
{
    /// <summary>Initialises the <see cref="DetailPanel"/>.</summary>
    public DetailPanel()
    {
        InitializeComponent();
    }

    /// <summary>
    /// Populates the panel with detail rows for <paramref name="gameObject"/>.
    /// Clears the panel when <paramref name="gameObject"/> is <see langword="null"/>.
    /// </summary>
    public void ShowObject(object? gameObject)
    {
        DetailList.Items.Clear();

        if (gameObject is null)
        {
            PanelTitle.Text = "Detail";
            return;
        }

        PanelTitle.Text = gameObject.GetType().Name.Replace("Record", "");

        foreach (var (label, value) in HexTooltip.DetailRows(gameObject))
        {
            DetailList.Items.Add(new DetailRow(label, value));
        }
    }

    private sealed record DetailRow(string Label, string Value);
}

using System.Windows;
using Microsoft.Win32;

namespace WitpaeTheaterStaff.Config;

/// <summary>Modal settings dialog for editing <see cref="AppSettings"/>.</summary>
public partial class SettingsWindow : Window
{
    private readonly AppSettings _settings;

    /// <summary>
    /// Gets <see langword="true"/> if the user clicked Save.
    /// </summary>
    public bool Saved { get; private set; }

    /// <summary>
    /// Creates and initialises the dialog with the given <paramref name="settings"/>.
    /// </summary>
    public SettingsWindow(AppSettings settings, Window owner)
    {
        ArgumentNullException.ThrowIfNull(settings);
        _settings = settings;
        Owner     = owner;
        InitializeComponent();
        Populate();
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    private void Populate()
    {
        GameDirBox.Text  = _settings.GameDir;
        SaveDirBox.Text  = _settings.SaveDir;
        SodFileBox.Text  = _settings.StartOfDayFile;
        EodFileBox.Text  = _settings.EndOfDayFile;
        SideCombo.SelectedIndex = _settings.Side == "JAPAN" ? 1 : 0;
    }

    // ── Browse handlers ───────────────────────────────────────────────────

    private void BrowseGameDir_Click(object sender, RoutedEventArgs e) =>
        PickFolder("Select WITPAE game directory", GameDirBox);

    private void BrowseSaveDir_Click(object sender, RoutedEventArgs e) =>
        PickFolder("Select save-file directory", SaveDirBox);

    private void BrowseSod_Click(object sender, RoutedEventArgs e) =>
        PickFile("Start-of-day save file", SodFileBox);

    private void BrowseEod_Click(object sender, RoutedEventArgs e) =>
        PickFile("End-of-day save file", EodFileBox);

    private static void PickFolder(string title, System.Windows.Controls.TextBox target)
    {
        var dlg = new OpenFolderDialog { Title = title };
        if (dlg.ShowDialog() == true)
            target.Text = dlg.FolderName;
    }

    private static void PickFile(string title, System.Windows.Controls.TextBox target)
    {
        var dlg = new OpenFileDialog
        {
            Title  = title,
            Filter = "PWS save files (*.pws)|*.pws|All files (*.*)|*.*",
        };
        if (dlg.ShowDialog() == true)
            target.Text = dlg.FileName;
    }

    // ── Dialog buttons ────────────────────────────────────────────────────

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        _settings.GameDir        = GameDirBox.Text.Trim();
        _settings.SaveDir        = SaveDirBox.Text.Trim();
        _settings.StartOfDayFile = SodFileBox.Text.Trim();
        _settings.EndOfDayFile   = EodFileBox.Text.Trim();
        _settings.Side = ((System.Windows.Controls.ComboBoxItem)SideCombo.SelectedItem).Content.ToString()
                         ?? "ALLIED";
        _settings.Save();
        Saved = true;
        Close();
    }

    private void Cancel_Click(object sender, RoutedEventArgs e) => Close();
}

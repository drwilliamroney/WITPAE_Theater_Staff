using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using WitpaeTheaterStaff.Config;
using WitpaeTheaterStaff.Data;
using WitpaeTheaterStaff.Data.Models;
using WitpaeTheaterStaff.UI;

namespace WitpaeTheaterStaff;

/// <summary>
/// Root application window: toolbar, zoomable/scrollable map canvas, and
/// detail panel.  Orchestrates <see cref="GameDataScraper"/>,
/// <see cref="TurnWatcher"/>, <see cref="OverlayBuilder"/>, and the map
/// background image.
/// </summary>
public partial class MainWindow : Window
{
    // ── Fields ────────────────────────────────────────────────────────────
    private AppSettings     _settings;
    private GameState       _state = GameState.Empty;
    private GameDataScraper? _scraper;
    private TurnWatcher?    _watcher;
    private OverlayBuilder? _overlayBuilder;
    private Image?          _mapImage;
    private double          _zoom = 1.0;

    private const double MapBaseWidth  = 1400.0;
    private const double MapBaseHeight =  900.0;

    // ── Constructor ───────────────────────────────────────────────────────

    /// <summary>Initialises the main window.</summary>
    public MainWindow()
    {
        InitializeComponent();

        _settings = App.Settings;
        ApplySettingsToToolbar();

        Loaded += OnLoaded;
        Closed += OnClosed;
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        // Build the map image
        RefreshMap();

        // Start watching for new turns
        StartWatcher();

        // Load data
        LoadData();
    }

    private void OnClosed(object sender, EventArgs e)
    {
        _watcher?.Dispose();
        _scraper?.Dispose();
    }

    // ── Data loading ──────────────────────────────────────────────────────

    private void LoadData()
    {
        if (!_settings.IsComplete)
        {
            WatchLabel.Text = "Watching: save dir not found";
            return;
        }

        _scraper?.Dispose();
        _scraper = new GameDataScraper(
            _settings.GameDir,
            _settings.EffectiveSodFile,
            _settings.EffectiveEodFile,
            _settings.Side);

        _state = _scraper.Load();
        RefreshOverlays();
        UpdateStatusBar();
    }

    private void RefreshMap()
    {
        MapCanvas.Children.Clear();

        BitmapSource mapBmp = MapAssembly.Assemble(_settings.GameDir);

        _mapImage = new Image
        {
            Source  = mapBmp,
            Width   = MapBaseWidth  * _zoom,
            Height  = MapBaseHeight * _zoom,
            Stretch = Stretch.Fill,
        };
        Canvas.SetLeft(_mapImage, 0);
        Canvas.SetTop(_mapImage,  0);
        MapCanvas.Children.Add(_mapImage);

        MapCanvas.Width  = MapBaseWidth  * _zoom;
        MapCanvas.Height = MapBaseHeight * _zoom;

        // Create overlay builder and add its canvases
        var transform = new CoordinateTransform(MapBaseWidth, MapBaseHeight, _zoom);
        _overlayBuilder = new OverlayBuilder(transform);

        foreach (var c in _overlayBuilder.AllCanvases)
        {
            c.Width  = MapBaseWidth  * _zoom;
            c.Height = MapBaseHeight * _zoom;
            Canvas.SetLeft(c, 0);
            Canvas.SetTop(c,  0);
            MapCanvas.Children.Add(c);
        }

        // Apply current overlay visibility settings
        ApplyOverlayVisibility();
    }

    private void RefreshOverlays()
    {
        if (_overlayBuilder is null) return;
        _overlayBuilder.Build(_state);
        ApplyOverlayVisibility();

        TurnLabel.Text = $"Turn: {_state.TurnInfo.GameTurn}";
        DateLabel.Text = _state.TurnInfo.GameDate is { Length: > 0 } d
            ? $"Date: {d}" : "Date: —";
    }

    // ── Overlay visibility ────────────────────────────────────────────────

    private void ApplyOverlayVisibility()
    {
        if (_overlayBuilder is null) return;

        foreach (var c in _overlayBuilder.AllCanvases)
        {
            if (c.Tag is not string tag) continue;
            bool visible = tag switch
            {
                "overlay_region" => _settings.ShowRegions,
                "overlay_tf"     => _settings.ShowTaskForces,
                "overlay_ship"   => _settings.ShowShips,
                "overlay_base"   => _settings.ShowBases,
                "overlay_air"    => _settings.ShowAir,
                "overlay_land"   => _settings.ShowLand,
                "overlay_threat" => _settings.ShowThreats,
                _                => true,
            };
            c.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
        }
    }

    private void ApplySettingsToToolbar()
    {
        SetToggle(ToggleRegions, _settings.ShowRegions);
        SetToggle(ToggleTF,      _settings.ShowTaskForces);
        SetToggle(ToggleShips,   _settings.ShowShips);
        SetToggle(ToggleBases,   _settings.ShowBases);
        SetToggle(ToggleAir,     _settings.ShowAir);
        SetToggle(ToggleLand,    _settings.ShowLand);
        SetToggle(ToggleThreats, _settings.ShowThreats);

        // Set side combo
        int idx = _settings.Side == "JAPAN" ? 1 : 0;
        if (SideCombo.Items.Count > idx) SideCombo.SelectedIndex = idx;
    }

    private static void SetToggle(ToggleButton btn, bool value) =>
        btn.IsChecked = value;

    // ── TurnWatcher ───────────────────────────────────────────────────────

    private void StartWatcher()
    {
        _watcher?.Dispose();
        _watcher = new TurnWatcher(_settings.EffectiveEodFile);
        _watcher.NewTurnDetected += (_, _) =>
            Dispatcher.Invoke(() =>
            {
                WatchLabel.Text = $"New turn @ {DateTime.Now:HH:mm:ss} — reloading…";
                LoadData();
            });

        WatchLabel.Text = File.Exists(_settings.EffectiveEodFile)
            ? $"Watching: {Path.GetFileName(_settings.EffectiveEodFile)}"
            : "Watching: file not found";
    }

    // ── Status bar ────────────────────────────────────────────────────────

    private void UpdateStatusBar()
    {
        ShipCountLabel.Text = $"Ships: {_state.Ships.Count}";
        AirCountLabel.Text  = $"Air: {_state.AirGroups.Count}";
        LandCountLabel.Text = $"Land: {_state.GroundUnits.Count}";
        BaseCountLabel.Text = $"Bases: {_state.Bases.Count}";
    }

    // ── Event handlers ────────────────────────────────────────────────────

    private void Settings_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new SettingsWindow(_settings, this);
        dlg.ShowDialog();
        if (dlg.Saved)
        {
            _zoom = _settings.Zoom;
            ApplySettingsToToolbar();
            RefreshMap();
            StartWatcher();
            LoadData();
        }
    }

    private void Reload_Click(object sender, RoutedEventArgs e) => LoadData();

    private void Exit_Click(object sender, RoutedEventArgs e) => Close();

    private void SideCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (SideCombo.SelectedItem is ComboBoxItem item)
        {
            string side = item.Content.ToString() ?? "ALLIED";
            if (side != _settings.Side)
            {
                _settings.Side = side;
                LoadData();
            }
        }
    }

    private void OverlayToggle_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not ToggleButton btn) return;
        bool visible = btn.IsChecked == true;

        switch (btn.Tag?.ToString())
        {
            case "overlay_region": _settings.ShowRegions    = visible; break;
            case "overlay_tf":     _settings.ShowTaskForces = visible; break;
            case "overlay_ship":   _settings.ShowShips      = visible; break;
            case "overlay_base":   _settings.ShowBases      = visible; break;
            case "overlay_air":    _settings.ShowAir        = visible; break;
            case "overlay_land":   _settings.ShowLand       = visible; break;
            case "overlay_threat": _settings.ShowThreats    = visible; break;
        }
        ApplyOverlayVisibility();
    }

    // ── Map mouse interaction ─────────────────────────────────────────────

    private void MapScrollViewer_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
    {
        if (Keyboard.Modifiers != ModifierKeys.Control) return;

        double factor = e.Delta > 0 ? 1.15 : (1.0 / 1.15);
        _zoom = Math.Clamp(_zoom * factor, 0.25, 4.0);
        _settings.Zoom = _zoom;

        // Rebuild map and overlays at new zoom
        RefreshMap();
        RefreshOverlays();
        e.Handled = true;
    }

    private void MapCanvas_MouseMove(object sender, MouseEventArgs e)
    {
        if (_overlayBuilder is null) return;

        Point pos = e.GetPosition(MapCanvas);
        UIElement? hit = HitTestOverlay(pos);
        if (hit?.Tag is { } tag)
            MapCanvas.ToolTip = HexTooltip.Build(tag);
    }

    private void MapCanvas_MouseLeave(object sender, MouseEventArgs e)
    {
        MapCanvas.ToolTip = null;
    }

    private void MapCanvas_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (_overlayBuilder is null) return;

        Point pos = e.GetPosition(MapCanvas);
        UIElement? hit = HitTestOverlay(pos);
        if (hit?.Tag is { } tag)
            DetailPanel.ShowObject(tag);
    }

    private UIElement? HitTestOverlay(Point pos)
    {
        // Walk children in reverse (top-most canvas first), skip map image
        for (int i = MapCanvas.Children.Count - 1; i >= 0; i--)
        {
            if (MapCanvas.Children[i] is not Canvas oc) continue;
            if (oc.Visibility != Visibility.Visible) continue;

            foreach (UIElement child in oc.Children)
            {
                if (!child.IsVisible) continue;
                var bounds = VisualTreeHelper.GetDescendantBounds(child);
                var offset = child.TranslatePoint(new Point(0, 0), MapCanvas);
                var rect   = new Rect(offset, new Size(bounds.Width, bounds.Height));
                if (rect.Contains(pos)) return child;
            }
        }
        return null;
    }
}

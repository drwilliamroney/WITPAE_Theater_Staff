using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace WitpaeTheaterStaff.Config;

/// <summary>
/// JSON-persisted application settings.
/// Loaded from and saved to
/// <c>%APPDATA%\WitpaeTheaterStaff\settings.json</c>.
/// </summary>
public sealed class AppSettings
{
    // ── Defaults ──────────────────────────────────────────────────────────

    /// <summary>Default game installation directory.</summary>
    public const string DefaultGameDir =
        @"C:\Matrix Games\War in the Pacific Admiral's Edition";

    /// <summary>Default save-file directory (<c>&lt;GameDir&gt;\SAVE</c>).</summary>
    public static string DefaultSaveDir =>
        Path.Combine(DefaultGameDir, "SAVE");

    // ── Persisted properties ──────────────────────────────────────────────

    /// <summary>Game installation directory (contains DLLs and <c>ART\</c>).</summary>
    public string GameDir { get; set; } = DefaultGameDir;

    /// <summary>Save-file directory (contains <c>wpae000.pws</c> etc.).</summary>
    public string SaveDir { get; set; } = DefaultSaveDir;

    /// <summary>Explicit path to start-of-day save file; empty = auto-derive.</summary>
    public string StartOfDayFile { get; set; } = string.Empty;

    /// <summary>Explicit path to end-of-day save file; empty = auto-derive.</summary>
    public string EndOfDayFile { get; set; } = string.Empty;

    /// <summary>Active side: <c>"ALLIED"</c> or <c>"JAPAN"</c>.</summary>
    public string Side { get; set; } = "ALLIED";

    /// <summary>Zoom level for the map canvas.</summary>
    public double Zoom { get; set; } = 1.0;

    // Overlay visibility defaults
    /// <summary>Show theater region polygons.</summary>
    public bool ShowRegions  { get; set; } = true;
    /// <summary>Show task-force arrows.</summary>
    public bool ShowTaskForces { get; set; } = true;
    /// <summary>Show individual ship dots.</summary>
    public bool ShowShips    { get; set; } = false;
    /// <summary>Show base health circles.</summary>
    public bool ShowBases    { get; set; } = true;
    /// <summary>Show air-group dots.</summary>
    public bool ShowAir      { get; set; } = true;
    /// <summary>Show ground-unit markers.</summary>
    public bool ShowLand     { get; set; } = true;
    /// <summary>Show threat heat-map.</summary>
    public bool ShowThreats  { get; set; } = true;

    // ── Derived helpers ───────────────────────────────────────────────────

    /// <summary>
    /// Effective start-of-day file path, falling back to
    /// <c>&lt;SaveDir&gt;\wpae002.pws</c>.
    /// </summary>
    [JsonIgnore]
    public string EffectiveSodFile =>
        !string.IsNullOrWhiteSpace(StartOfDayFile)
            ? StartOfDayFile
            : Path.Combine(SaveDir, "wpae002.pws");

    /// <summary>
    /// Effective end-of-day file path, falling back to
    /// <c>&lt;SaveDir&gt;\wpae000.pws</c>.
    /// </summary>
    [JsonIgnore]
    public string EffectiveEodFile =>
        !string.IsNullOrWhiteSpace(EndOfDayFile)
            ? EndOfDayFile
            : Path.Combine(SaveDir, "wpae000.pws");

    /// <summary>
    /// Returns <see langword="true"/> when the game directory and both save
    /// files exist on disk.
    /// </summary>
    [JsonIgnore]
    public bool IsComplete =>
        Directory.Exists(GameDir) &&
        File.Exists(EffectiveSodFile) &&
        File.Exists(EffectiveEodFile);

    // ── Persistence ───────────────────────────────────────────────────────

    private static readonly JsonSerializerOptions SerializerOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,
    };

    private static string ConfigPath =>
        Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "WitpaeTheaterStaff",
            "settings.json");

    /// <summary>Loads settings from disk, returning defaults on any error.</summary>
    public static AppSettings Load()
    {
        string path = ConfigPath;
        if (!File.Exists(path)) return new AppSettings();

        try
        {
            using var fs = File.OpenRead(path);
            return JsonSerializer.Deserialize<AppSettings>(fs, SerializerOptions)
                   ?? new AppSettings();
        }
        catch (Exception ex)
        {
            Trace.TraceWarning($"Failed to load settings from {path}: {ex.Message}");
            return new AppSettings();
        }
    }

    /// <summary>Persists current settings to disk.</summary>
    public void Save()
    {
        string path = ConfigPath;
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        using var fs = File.Create(path);
        JsonSerializer.Serialize(fs, this, SerializerOptions);
        Trace.TraceInformation($"Settings saved to {path}");
    }

    /// <summary>
    /// Applies values from command-line arguments or environment variables.
    /// Accepts: <c>--side</c>, <c>--game-path</c>, <c>--save-path</c>.
    /// </summary>
    public void ApplyArgs(IReadOnlyList<string> args)
    {
        for (int i = 0; i < args.Count - 1; i++)
        {
            switch (args[i].ToLowerInvariant())
            {
                case "--side":
                    Side = args[i + 1].ToUpperInvariant() switch
                    {
                        "JAPAN"  => "JAPAN",
                        "ALLIED" => "ALLIED",
                        "ALLIES" => "ALLIED",
                        _        => Side,
                    };
                    i++;
                    break;
                case "--game-path":
                    GameDir = args[i + 1];
                    i++;
                    break;
                case "--save-path":
                    SaveDir = args[i + 1];
                    i++;
                    break;
            }
        }
    }
}

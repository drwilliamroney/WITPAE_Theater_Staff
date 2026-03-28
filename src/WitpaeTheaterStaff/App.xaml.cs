using System.Windows;
using WitpaeTheaterStaff.Config;

namespace WitpaeTheaterStaff;

/// <summary>WPF application entry point.</summary>
public partial class App : Application
{
    /// <summary>Application-wide settings instance, available after startup.</summary>
    public static AppSettings Settings { get; private set; } = new();

    /// <inheritdoc/>
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        Settings = AppSettings.Load();
        Settings.ApplyArgs(e.Args);
    }
}

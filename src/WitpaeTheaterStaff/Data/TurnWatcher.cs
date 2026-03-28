using System.Diagnostics;

namespace WitpaeTheaterStaff.Data;

/// <summary>
/// Watches a save file for modification-time changes and raises
/// <see cref="NewTurnDetected"/> whenever the file changes.
/// </summary>
/// <remarks>
/// Uses <see cref="FileSystemWatcher"/> for efficient OS-level notification
/// rather than polling.  A timer-based debounce avoids multiple rapid
/// notifications when the game writes the file in several passes.
/// </remarks>
public sealed class TurnWatcher : IDisposable
{
    private FileSystemWatcher? _watcher;
    private System.Threading.Timer? _debounceTimer;
    private bool _disposed;

    /// <summary>Raised on the thread-pool when a new turn save file is detected.</summary>
    public event EventHandler? NewTurnDetected;

    /// <summary>
    /// Creates a <see cref="TurnWatcher"/> that monitors <paramref name="eodFilePath"/>.
    /// </summary>
    /// <param name="eodFilePath">
    /// Full path to the end-of-day save file to watch (e.g. <c>wpae000.pws</c>).
    /// </param>
    /// <param name="debounceMs">
    /// Milliseconds to wait after the last file-changed event before firing
    /// <see cref="NewTurnDetected"/> (default: 2 000 ms).
    /// </param>
    public TurnWatcher(string eodFilePath, int debounceMs = 2_000)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(eodFilePath);

        string? dir = Path.GetDirectoryName(eodFilePath);
        string  file = Path.GetFileName(eodFilePath);

        if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir))
        {
            Trace.TraceWarning($"TurnWatcher: directory not found ({dir}); watcher inactive.");
            return;
        }

        _watcher = new FileSystemWatcher(dir, file)
        {
            NotifyFilter = NotifyFilters.LastWrite | NotifyFilters.Size,
            EnableRaisingEvents = true,
        };

        _watcher.Changed += (_, _) => Debounce(debounceMs);
        _watcher.Created += (_, _) => Debounce(debounceMs);
    }

    // ── Public API ────────────────────────────────────────────────────────

    /// <summary>
    /// Updates the watched file path at runtime (e.g. after the user changes
    /// settings).
    /// </summary>
    public void UpdateFile(string eodFilePath)
    {
        if (_disposed) return;

        string? dir  = Path.GetDirectoryName(eodFilePath);
        string  file = Path.GetFileName(eodFilePath);

        if (_watcher is not null && !string.IsNullOrEmpty(dir) && Directory.Exists(dir))
        {
            _watcher.Path   = dir;
            _watcher.Filter = file;
        }
    }

    // ── Internal helpers ──────────────────────────────────────────────────

    private void Debounce(int ms)
    {
        _debounceTimer?.Dispose();
        _debounceTimer = new System.Threading.Timer(_ =>
        {
            Trace.TraceInformation("TurnWatcher: new turn detected.");
            NewTurnDetected?.Invoke(this, EventArgs.Empty);
        }, null, ms, Timeout.Infinite);
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _watcher?.Dispose();
        _debounceTimer?.Dispose();
    }
}

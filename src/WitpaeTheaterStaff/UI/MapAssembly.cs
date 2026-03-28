using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace WitpaeTheaterStaff.UI;

/// <summary>
/// Assembles the Pacific theater base map from the 42 BMP tile files
/// shipped with the game (<c>WPEN00.bmp</c> … <c>WPEN41.bmp</c> in
/// the <c>ART</c> subdirectory).
/// </summary>
/// <remarks>
/// Returns a placeholder <see cref="BitmapSource"/> when tiles are not found,
/// so the application runs without a game installation.
/// </remarks>
public static class MapAssembly
{
    private const int TileCols = 7;
    private const int TileRows = 6;
    private const string TilePattern = "WPEN{0:D2}.bmp";

    /// <summary>
    /// Returns the assembled map as a <see cref="BitmapSource"/>.
    /// </summary>
    /// <param name="gameDir">
    /// Root WITPAE installation directory containing the <c>ART</c> folder.
    /// Pass <see langword="null"/> to get the placeholder immediately.
    /// </param>
    public static BitmapSource Assemble(string? gameDir)
    {
        if (!string.IsNullOrEmpty(gameDir))
        {
            string artDir = Path.Combine(gameDir, "ART");
            var result = TryFromTiles(artDir);
            if (result is not null)
            {
                Trace.TraceInformation($"Map assembled from tiles in {artDir}");
                return result;
            }
        }

        Trace.TraceWarning("Map tiles not found; using placeholder.");
        return Placeholder();
    }

    // ── Private helpers ───────────────────────────────────────────────────

    private static BitmapSource? TryFromTiles(string artDir)
    {
        try
        {
            if (!Directory.Exists(artDir)) return null;

            var tilePaths = Enumerable.Range(0, TileCols * TileRows)
                .Select(i => Path.Combine(artDir, string.Format(TilePattern, i)))
                .ToArray();

            if (tilePaths.Any(p => !File.Exists(p))) return null;

            var tiles = tilePaths
                .Select(p =>
                {
                    var img = new BitmapImage();
                    img.BeginInit();
                    img.CacheOption = BitmapCacheOption.OnLoad;
                    using (var s = File.OpenRead(p))
                    {
                        img.StreamSource = s;
                        img.EndInit();
                    }
                    img.Freeze();
                    return img;
                })
                .ToArray();

            // Compute per-column widths and per-row heights
            int[] colWidths  = new int[TileCols];
            int[] rowHeights = new int[TileRows];
            for (int idx = 0; idx < tiles.Length; idx++)
            {
                int row = idx / TileCols;
                int col = idx % TileCols;
                colWidths[col]  = Math.Max(colWidths[col],  tiles[idx].PixelWidth);
                rowHeights[row] = Math.Max(rowHeights[row], tiles[idx].PixelHeight);
            }

            int totalW = colWidths.Sum();
            int totalH = rowHeights.Sum();

            // Compute tile paste offsets
            int[] xOffsets = new int[TileCols];
            int[] yOffsets = new int[TileRows];
            for (int c = 1; c < TileCols; c++) xOffsets[c] = xOffsets[c - 1] + colWidths[c - 1];
            for (int r = 1; r < TileRows; r++) yOffsets[r] = yOffsets[r - 1] + rowHeights[r - 1];

            // Composite into a WriteableBitmap
            var composite = new WriteableBitmap(totalW, totalH, 96, 96, PixelFormats.Bgr32, null);

            for (int idx = 0; idx < tiles.Length; idx++)
            {
                int row = idx / TileCols;
                int col = idx % TileCols;

                var converted = new FormatConvertedBitmap(tiles[idx], PixelFormats.Bgr32, null, 0);
                int w = converted.PixelWidth;
                int h = converted.PixelHeight;
                int stride = w * 4;
                byte[] pixels = new byte[stride * h];
                converted.CopyPixels(pixels, stride, 0);

                composite.WritePixels(
                    new System.Windows.Int32Rect(xOffsets[col], yOffsets[row], w, h),
                    pixels, stride, 0);
            }

            composite.Freeze();
            return composite;
        }
        catch (Exception ex)
        {
            Trace.TraceError($"Failed to assemble map from tiles: {ex.Message}");
            return null;
        }
    }

    private static BitmapSource Placeholder()
    {
        const int W = 1400, H = 900;
        var bmp = new WriteableBitmap(W, H, 96, 96, PixelFormats.Bgr32, null);

        // Fill with ocean-blue
        int stride = W * 4;
        byte[] pixels = new byte[stride * H];
        for (int i = 0; i < pixels.Length; i += 4)
        {
            pixels[i + 0] = 64;   // B
            pixels[i + 1] = 36;   // G
            pixels[i + 2] = 20;   // R
        }

        // Draw grid lines (slightly lighter)
        for (int gx = 0; gx < W; gx += 100)
            for (int y = 0; y < H; y++)
            {
                int p = (y * stride) + gx * 4;
                pixels[p] = pixels[p + 1] = pixels[p + 2] = 85;
            }
        for (int gy = 0; gy < H; gy += 100)
            for (int x = 0; x < W; x++)
            {
                int p = (gy * stride) + x * 4;
                pixels[p] = pixels[p + 1] = pixels[p + 2] = 85;
            }

        bmp.WritePixels(new System.Windows.Int32Rect(0, 0, W, H), pixels, stride, 0);
        bmp.Freeze();
        return bmp;
    }
}

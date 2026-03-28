"""WITPAE Theater Staff — application entry point.

Launch with:
    python src/witpae_theater_staff/main.py
or via the provided run_gui.bat launcher on Windows.

Requires: 32-bit Python 3.10–3.13, wxPython 4.2.5.
"""

import logging
import sys

import wx

logger = logging.getLogger(__name__)

APP_TITLE = "WITPAE Theater Staff"


class MainFrame(wx.Frame):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__(
            parent=None,
            title=APP_TITLE,
            size=(1200, 800),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self._build_ui()
        self.Centre()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construct the main window layout."""
        # ── Root sizer: layer panel | map+info column ─────────────────────────
        root_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # ── Layer toggle panel (left) ─────────────────────────────────────────
        layer_panel = self._make_layer_panel()
        root_sizer.Add(layer_panel, 0, wx.EXPAND | wx.ALL, 4)

        # ── Right column: map canvas + info panel ─────────────────────────────
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        map_placeholder = self._make_map_placeholder()
        right_sizer.Add(map_placeholder, 1, wx.EXPAND | wx.ALL, 4)

        info_panel = self._make_info_panel()
        right_sizer.Add(info_panel, 0, wx.EXPAND | wx.ALL, 4)

        root_sizer.Add(right_sizer, 1, wx.EXPAND)

        # ── Status bar ────────────────────────────────────────────────────────
        self.CreateStatusBar(3)
        self.SetStatusWidths([-1, 200, 160])
        self.SetStatusText("Ready", 0)
        self.SetStatusText("No save file loaded", 1)
        self.SetStatusText("", 2)

        # ── Apply ─────────────────────────────────────────────────────────────
        panel = wx.Panel(self)
        panel.SetSizer(root_sizer)
        frame_sizer = wx.BoxSizer()
        frame_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)
        self.Layout()

    def _make_layer_panel(self) -> wx.Panel:
        """Build the left-hand overlay layer toggle panel."""
        panel = wx.Panel(self, size=(160, -1))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Overlay Layers")
        title.SetFont(
            title.GetFont().Bold()
        )
        sizer.Add(title, 0, wx.ALL, 6)
        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)

        # Placeholder layer checkboxes — will be replaced by OverlayManager
        # wiring once the overlay system is implemented.
        _PLACEHOLDER_LAYERS = [
            "Regions",
            "Bases",
            "Task Forces",
            "Threats",
            "Air Groups",
            "Ground Units",
            "Sea Areas",
        ]
        for name in _PLACEHOLDER_LAYERS:
            cb = wx.CheckBox(panel, label=name)
            cb.SetValue(True)
            sizer.Add(cb, 0, wx.ALL, 4)

        panel.SetSizer(sizer)
        return panel

    def _make_map_placeholder(self) -> wx.Panel:
        """Placeholder for the MapPanel (wx.ScrolledWindow + wx.GraphicsContext).

        This will be replaced with the full MapPanel implementation once the
        overlay and coordinate-transform modules are in place.
        """
        panel = wx.Panel(self, style=wx.SUNKEN_BORDER)
        panel.SetBackgroundColour(wx.Colour(26, 58, 26))  # dark map green

        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(
            panel,
            label="[ Map canvas — coming soon ]\n\nWill display the WitPAE map with\nalpha-blended overlay layers via\nwx.GraphicsContext.",
            style=wx.ALIGN_CENTRE_HORIZONTAL,
        )
        label.SetForegroundColour(wx.Colour(76, 175, 80))
        label.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        sizer.AddStretchSpacer()
        sizer.Add(label, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        sizer.AddStretchSpacer()
        panel.SetSizer(sizer)
        return panel

    def _make_info_panel(self) -> wx.Panel:
        """Build the click-through information panel below the map."""
        panel = wx.Panel(self, size=(-1, 140))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Hex Information  (click map to populate)")
        title.SetFont(title.GetFont().Bold())
        sizer.Add(title, 0, wx.ALL, 6)

        self._info_text = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_SUNKEN,
        )
        self._info_text.SetFont(
            wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        )
        sizer.Add(self._info_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

        panel.SetSizer(sizer)
        return panel


def main() -> None:
    """Create and run the WITPAE Theater Staff application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = wx.App(redirect=False)
    frame = MainFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()

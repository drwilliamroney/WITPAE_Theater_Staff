"""Persistent application settings stored as a JSON file.

Settings are loaded from / saved to ``~/.witpae_theater_staff/settings.json``
(or the path returned by ``Settings.config_path()``).

A modal Tkinter dialog (`SettingsDialog`) lets the user view and edit all
settings from within the running GUI.
"""

from __future__ import annotations

import json
import logging
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import tkinter.ttk as ttk
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

_DEFAULT_GAME_DIR = r"C:\Matrix Games\War in the Pacific Admiral's Edition"
_DEFAULT_SAVE_DIR = r"C:\Matrix Games\War in the Pacific Admiral's Edition\SAVE"


class Settings:
    """JSON-backed application settings."""

    def __init__(self) -> None:
        self.game_dir: str = _DEFAULT_GAME_DIR
        self.save_dir: str = _DEFAULT_SAVE_DIR
        self.start_of_day_file: str = ""
        self.end_of_day_file: str = ""
        self.side: str = "ALLIED"        # "ALLIED" | "JAPAN"
        self.poll_interval: int = 30     # seconds between save-file polls
        self.zoom: float = 1.0
        self.overlay_region: bool = True
        self.overlay_tf: bool = True
        self.overlay_ship: bool = False
        self.overlay_base: bool = True
        self.overlay_air: bool = True
        self.overlay_land: bool = True
        self.overlay_threat: bool = True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def config_path() -> Path:
        """Return the canonical path to the settings JSON file."""
        return Path.home() / ".witpae_theater_staff" / "settings.json"

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from disk, returning defaults on any error."""
        settings = cls()
        path = cls.config_path()
        if path.exists():
            try:
                with path.open(encoding="utf-8") as fh:
                    data: dict[str, Any] = json.load(fh)
                for key, value in data.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
                LOGGER.debug("Settings loaded from %s", path)
            except Exception as exc:
                LOGGER.warning("Failed to load settings (%s); using defaults.", exc)
        return settings

    def save(self) -> None:
        """Persist current settings to disk."""
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.__dict__, fh, indent=2)
        LOGGER.debug("Settings saved to %s", path)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def effective_sod_file(self) -> Path:
        """Return start-of-day file path, defaulting to wpae002.pws in save_dir."""
        if self.start_of_day_file:
            return Path(self.start_of_day_file)
        return Path(self.save_dir) / "wpae002.pws"

    @property
    def effective_eod_file(self) -> Path:
        """Return end-of-day file path, defaulting to wpae000.pws in save_dir."""
        if self.end_of_day_file:
            return Path(self.end_of_day_file)
        return Path(self.save_dir) / "wpae000.pws"

    def is_complete(self) -> bool:
        """Return True when all required paths exist on disk."""
        return (
            Path(self.game_dir).is_dir()
            and self.effective_sod_file.exists()
            and self.effective_eod_file.exists()
        )


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

class SettingsDialog(tk.Toplevel):
    """Modal dialog for editing application settings."""

    def __init__(self, parent: tk.Widget, settings: Settings) -> None:
        super().__init__(parent)
        self.title("WITPAE Theater Staff — Settings")
        self.resizable(False, False)
        self.grab_set()

        self._settings = settings
        self._saved = False

        self._build_ui()
        self._populate()
        self.wait_window(self)

    @property
    def saved(self) -> bool:
        """True if the user accepted the dialog (clicked Save)."""
        return self._saved

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # ── Game directory ────────────────────────────────────────────
        ttk.Label(self, text="Game directory:").grid(row=0, column=0, sticky="w", **pad)
        self._game_dir_var = tk.StringVar()
        ttk.Entry(self, textvariable=self._game_dir_var, width=48).grid(row=0, column=1, **pad)
        ttk.Button(self, text="Browse…", command=self._browse_game_dir).grid(row=0, column=2, **pad)

        # ── Save directory ────────────────────────────────────────────
        ttk.Label(self, text="Save directory:").grid(row=1, column=0, sticky="w", **pad)
        self._save_dir_var = tk.StringVar()
        ttk.Entry(self, textvariable=self._save_dir_var, width=48).grid(row=1, column=1, **pad)
        ttk.Button(self, text="Browse…", command=self._browse_save_dir).grid(row=1, column=2, **pad)

        # ── SOD file ──────────────────────────────────────────────────
        ttk.Label(self, text="Start-of-day file (wpae002.pws):").grid(row=2, column=0, sticky="w", **pad)
        self._sod_var = tk.StringVar()
        ttk.Entry(self, textvariable=self._sod_var, width=48).grid(row=2, column=1, **pad)
        ttk.Button(self, text="Browse…", command=self._browse_sod).grid(row=2, column=2, **pad)

        # ── EOD file ──────────────────────────────────────────────────
        ttk.Label(self, text="End-of-day file (wpae000.pws):").grid(row=3, column=0, sticky="w", **pad)
        self._eod_var = tk.StringVar()
        ttk.Entry(self, textvariable=self._eod_var, width=48).grid(row=3, column=1, **pad)
        ttk.Button(self, text="Browse…", command=self._browse_eod).grid(row=3, column=2, **pad)

        # ── Side ──────────────────────────────────────────────────────
        ttk.Label(self, text="Side:").grid(row=4, column=0, sticky="w", **pad)
        self._side_var = tk.StringVar()
        ttk.Combobox(
            self,
            textvariable=self._side_var,
            values=["ALLIED", "JAPAN"],
            state="readonly",
            width=10,
        ).grid(row=4, column=1, sticky="w", **pad)

        # ── Poll interval ─────────────────────────────────────────────
        ttk.Label(self, text="Auto-refresh interval (sec):").grid(row=5, column=0, sticky="w", **pad)
        self._poll_var = tk.IntVar()
        ttk.Spinbox(self, textvariable=self._poll_var, from_=5, to=300, width=8).grid(
            row=5, column=1, sticky="w", **pad
        )

        # ── Buttons ───────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=12)
        ttk.Button(btn_frame, text="Save", command=self._on_save).grid(row=0, column=0, padx=6)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).grid(row=0, column=1, padx=6)

    def _populate(self) -> None:
        s = self._settings
        self._game_dir_var.set(s.game_dir)
        self._save_dir_var.set(s.save_dir)
        self._sod_var.set(s.start_of_day_file)
        self._eod_var.set(s.end_of_day_file)
        self._side_var.set(s.side)
        self._poll_var.set(s.poll_interval)

    # ------------------------------------------------------------------
    # Browse helpers
    # ------------------------------------------------------------------

    def _browse_game_dir(self) -> None:
        path = fd.askdirectory(title="Select WITPAE game directory")
        if path:
            self._game_dir_var.set(path)

    def _browse_save_dir(self) -> None:
        path = fd.askdirectory(title="Select save-file directory")
        if path:
            self._save_dir_var.set(path)

    def _browse_sod(self) -> None:
        path = fd.askopenfilename(
            title="Select start-of-day save file",
            filetypes=[("PWS save files", "*.pws"), ("All files", "*.*")],
        )
        if path:
            self._sod_var.set(path)

    def _browse_eod(self) -> None:
        path = fd.askopenfilename(
            title="Select end-of-day save file",
            filetypes=[("PWS save files", "*.pws"), ("All files", "*.*")],
        )
        if path:
            self._eod_var.set(path)

    # ------------------------------------------------------------------
    # Save callback
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        s = self._settings
        s.game_dir = self._game_dir_var.get().strip()
        s.save_dir = self._save_dir_var.get().strip()
        s.start_of_day_file = self._sod_var.get().strip()
        s.end_of_day_file = self._eod_var.get().strip()
        s.side = self._side_var.get()
        try:
            s.poll_interval = int(self._poll_var.get())
        except ValueError:
            mb.showerror("Invalid value", "Poll interval must be a whole number of seconds.")
            return
        s.save()
        self._saved = True
        self.destroy()

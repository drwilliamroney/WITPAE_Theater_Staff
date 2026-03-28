"""Background save-file watcher.

Polls the modification time of the end-of-day save file on a background
thread and calls ``on_new_turn`` whenever it changes.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable

LOGGER = logging.getLogger(__name__)


class TurnWatcher:
    """Watch a save file for modification and invoke a callback on change.

    Parameters
    ----------
    eod_file:
        Path to the end-of-day ``.pws`` file to watch.
    on_new_turn:
        Callable invoked (from the watcher thread) when the file changes.
    poll_interval:
        Seconds between polls (default: 30).
    """

    def __init__(
        self,
        eod_file: Path,
        on_new_turn: Callable[[], None],
        poll_interval: float = 30.0,
    ) -> None:
        self._eod_file = Path(eod_file)
        self._on_new_turn = on_new_turn
        self._poll_interval = poll_interval
        self._last_mtime: float | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background polling thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._last_mtime = self._current_mtime()
        self._thread = threading.Thread(
            target=self._run,
            name="TurnWatcher",
            daemon=True,
        )
        self._thread.start()
        LOGGER.debug("TurnWatcher started; watching %s", self._eod_file)

    def stop(self) -> None:
        """Stop the background polling thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval + 5)
        LOGGER.debug("TurnWatcher stopped")

    def update_file(self, eod_file: Path) -> None:
        """Change the watched file path at runtime."""
        self._eod_file = Path(eod_file)
        self._last_mtime = self._current_mtime()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _current_mtime(self) -> float | None:
        """Return the modification time of the watched file, or None."""
        try:
            return self._eod_file.stat().st_mtime
        except OSError:
            return None

    def _run(self) -> None:
        while not self._stop_event.wait(self._poll_interval):
            mtime = self._current_mtime()
            if mtime is not None and mtime != self._last_mtime:
                LOGGER.info("Save file changed (%s); triggering new-turn callback", self._eod_file)
                self._last_mtime = mtime
                try:
                    self._on_new_turn()
                except Exception:
                    LOGGER.exception("Error in on_new_turn callback")

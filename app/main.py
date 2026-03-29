"""Entry point for the WITPAE Theater Staff PyQt5 app."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from app.logging_setup import configure_logging
from app.main_window import MainWindow


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI args for side and game directories."""
    parser = argparse.ArgumentParser(description="WITPAE Theater Staff")
    parser.add_argument("--side", default="allies", choices=["allies", "japan"], help="Side to display")
    parser.add_argument("--game-path", required=True, help="Root WITPAE game directory")
    parser.add_argument("--save-path", required=True, help="WITPAE SAVE directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the PyQt5 desktop app."""
    configure_logging()
    args = parse_args(argv if argv is not None else sys.argv[1:])

    app = QApplication(sys.argv)
    window = MainWindow(Path(args.game_path), Path(args.save_path), args.side.upper())
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

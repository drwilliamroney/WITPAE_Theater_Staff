"""Logging configuration for the WITPAE Theater Staff app."""

from __future__ import annotations

import logging

from rich.logging import RichHandler


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging with Rich formatting."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=False)],
    )

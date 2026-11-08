"""Minimal logging configuration shared by the CLI and API."""

import logging

from knowledge_config import LOG_LEVEL


def configure_logging() -> None:
    """Set one root level and a compact format without replacing existing handlers."""
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    if not isinstance(level, int):
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger().setLevel(level)

"""Structured logging for Sponge."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for Sponge.

    Args:
        level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    logger = logging.getLogger("sponge")
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper()))


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the 'sponge' namespace."""
    return logging.getLogger(f"sponge.{name}")

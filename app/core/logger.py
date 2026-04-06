"""Logging helpers.

Step 2B keeps logging lightweight; structured logging can be added later.
"""

from __future__ import annotations

import logging


def get_logger(name: str = "desktop_control_ai") -> logging.Logger:
    """Get a namespaced logger without side effects."""

    return logging.getLogger(name)


def configure_logging(level: int = logging.INFO) -> None:
    """Optional basic logging configuration.

    Not called automatically; runtime wiring will decide when to configure.
    """

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

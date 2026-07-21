"""automation_grid.logging_utils - structured logging setup for the skill."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from .config import LOG_DIR, LOG_LEVEL

_CONFIGURED = False


def get_logger(name: str = "automation-grid-game-design") -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger(name)
    if _CONFIGURED:
        return logger
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # stderr handler
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    # rotating file handler
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            LOG_DIR / "automation_grid.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        # read-only / restricted: keep stderr logging only
        pass
    _CONFIGURED = True
    return logger

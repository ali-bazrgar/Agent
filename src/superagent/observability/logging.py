from __future__ import annotations

import logging
from typing import Any

from superagent.config.settings import Settings


def configure_logging(settings: Settings | None = None) -> logging.Logger:
    """Configure application logging and return a logger."""

    resolved_settings = settings or Settings()
    logging.basicConfig(
        level=getattr(logging, resolved_settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("superagent")
    logger.setLevel(getattr(logging, resolved_settings.log_level.upper(), logging.INFO))
    return logger


def get_logger(name: str, **fields: Any) -> logging.Logger:
    """Return a logger that can include structured fields in the log record."""

    logger = logging.getLogger(name)
    return logger

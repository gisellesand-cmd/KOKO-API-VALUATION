from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
    merge_contextvars,
)

from .config import get_settings


def configure_logging(level: str | None = None) -> None:
    """Configure structlog and stdlib logging to emit structured JSON."""
    resolved_level = (level or get_settings().LOG_LEVEL).upper()
    numeric_level = getattr(logging, resolved_level, logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
        force=True,
    )

    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger."""
    return structlog.get_logger(name) if name else structlog.get_logger()


def bind_request_id(request_id: Any) -> None:
    """Bind a request_id to the current logging context."""
    bind_contextvars(request_id=str(request_id))


def clear_request_context() -> None:
    """Clear all bound contextvars from the current logging context."""
    clear_contextvars()


__all__ = [
    "configure_logging",
    "get_logger",
    "bind_request_id",
    "clear_request_context",
]

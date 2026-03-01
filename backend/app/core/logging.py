"""
CodeGuard AI — Structured Logging Configuration.

Uses structlog for JSON-formatted, context-rich logging.
Each log entry includes job_id and pipeline stage when available.
"""

import logging
import sys

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """Configure structlog with JSON output and stdlib integration."""

    # ── Shared processors ────────────────────────────────────────
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # ── Structlog configuration ──────────────────────────────────
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # ── Stdlib handler ───────────────────────────────────────────
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer()
            if settings.LOG_LEVEL == "DEBUG"
            else structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # ── Root logger ──────────────────────────────────────────────
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Quiet noisy libraries
    for name in ("uvicorn.access", "sqlalchemy.engine", "httpcore", "httpx"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named structlog logger instance."""
    return structlog.get_logger(name)

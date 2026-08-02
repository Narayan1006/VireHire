"""
VeriHire AI - Structured Logging Configuration

Provides structured JSON logging for production and human-readable
console logging for development.  Automatically redacts sensitive
values (API keys, tokens) from log output.

Usage:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Pipeline started", extra={"candidates": 9544})
"""

import logging
import re
import sys
from datetime import datetime, timezone
from typing import Optional

from pythonjsonlogger import jsonlogger


# ── Sensitive data patterns to redact ────────────────────────────
_REDACT_PATTERNS = [
    re.compile(r"(GROQ_API_KEY|groq_api_key)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"(GITHUB_TOKEN|github_token)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"(api_key|apikey|secret|token|password)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"(gsk_[A-Za-z0-9_]+)", re.IGNORECASE),        # Groq key pattern
    re.compile(r"(ghp_[A-Za-z0-9_]+)", re.IGNORECASE),         # GitHub token pattern
]

_REDACTION_PLACEHOLDER = "***REDACTED***"


def _redact(message: str) -> str:
    """Replace sensitive values in a log message with redaction placeholders."""
    for pattern in _REDACT_PATTERNS:
        message = pattern.sub(_REDACTION_PLACEHOLDER, message)
    return message


# ── Custom Formatters ────────────────────────────────────────────

class RedactingFormatter(logging.Formatter):
    """Console formatter that redacts sensitive data."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return _redact(original)


class RedactingJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that adds standard fields and redacts secrets."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        if record.exc_info and not log_record.get("exc_info"):
            log_record["exc_info"] = self.formatException(record.exc_info)

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return _redact(original)


# ── Logger Factory ───────────────────────────────────────────────

_configured = False


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
) -> None:
    """
    Configure the root logger for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True, use structured JSON output (production).
                     If False, use human-readable console output (development).
    """
    global _configured
    if _configured:
        return
    _configured = True

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        formatter = RedactingJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
        )
    else:
        formatter = RedactingFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a named logger.

    If logging has not been configured yet, it will be set up with
    sensible defaults (INFO level, console format).

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    if not _configured:
        setup_logging()
    return logging.getLogger(name or "verihire")

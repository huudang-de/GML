"""Structured JSON logging with request_id ContextVar.

Specifications:
- Spec §5 T5, §11.7
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class JsonRequestLogFormatter(logging.Formatter):
    """Custom formatter producing single-line JSON log events with context."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(""),
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def configure_structured_logging(level: str = "INFO") -> None:
    """Configure root logger with JsonRequestLogFormatter on stdout."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Avoid duplicate handlers
    for handler in list(root.handlers):
        root.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonRequestLogFormatter())
    root.addHandler(stream_handler)

"""
Central logging configuration that emits JSON lines for better observability.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, Optional

from .config import get_settings


class JsonFormatter(logging.Formatter):
    """Render log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        for key in ("request_id", "session_id"):
            value: Optional[Any] = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.stack_info:
            payload["stack_info"] = record.stack_info

        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure root logger for JSON structured output."""

    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    # Remove existing handlers so reconfiguration is idempotent.
    for existing in list(root.handlers):
        root.removeHandler(existing)

    root.addHandler(handler)

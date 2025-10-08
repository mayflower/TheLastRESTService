"""HTTP response helpers for consistent reply construction."""

from __future__ import annotations

from typing import Any, Dict


def make_response(status: int, body: Any | None = None, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    """Utility for creating HTTP-like dictionaries inside the sandbox."""

    if headers is None:
        headers = {}
    return {"status": status, "headers": headers, "body": body}


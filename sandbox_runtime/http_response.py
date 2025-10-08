"""HTTP response helpers for consistent reply construction."""

from __future__ import annotations

from typing import Any, Dict, Optional


def make_response(
    status: int,
    body: Any | None = None,
    headers: Optional[Dict[str, str]] = None,
    *,
    media_type: Optional[str] = None,
    is_json: bool = True,
) -> Dict[str, Any]:
    """Utility for creating HTTP-like dictionaries inside the sandbox."""

    final_headers: Dict[str, str] = dict(headers or {})
    if is_json and body is not None and "Content-Type" not in final_headers:
        final_headers["Content-Type"] = "application/json"
    if not is_json and media_type is None:
        media_type = "application/octet-stream"

    return {
        "status": status,
        "headers": final_headers,
        "body": body,
        "media_type": media_type,
        "is_json": is_json,
    }

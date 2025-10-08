"""
Exception types and handler registration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class SandboxExecutionError(Exception):
    """Raised when sandbox execution fails in a controlled manner."""

    def __init__(self, detail: str, *, status_code: int = 500, payload: Dict[str, Any] | None = None) -> None:
        self.detail = detail
        self.status_code = status_code
        self.payload = payload or {}
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach module exception handlers to the FastAPI app."""

    @app.exception_handler(SandboxExecutionError)
    async def sandbox_error_handler(request: Request, exc: SandboxExecutionError) -> JSONResponse:
        logger.error(
            "sandbox_error",
            extra={
                "request_id": request.headers.get("X-Request-ID"),
                "session_id": request.headers.get("X-Session-ID"),
            },
        )
        body = {"error": exc.detail}
        if exc.payload:
            body["details"] = exc.payload
        return JSONResponse(status_code=exc.status_code, content=body)

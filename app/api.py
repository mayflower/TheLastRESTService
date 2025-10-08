"""
API request orchestration for the catch-all route.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Mapping, Optional, TypedDict

from fastapi import Depends, Request
from fastapi.responses import JSONResponse, Response

from .errors import SandboxExecutionError
from .sandbox import SandboxManager, SandboxResponse
from .security import SessionContext, session_dependency

logger = logging.getLogger(__name__)


class RequestContext(TypedDict, total=False):
    method: str
    path: str
    segments: List[str]
    query: Dict[str, List[str]]
    headers: Dict[str, str]
    body_json: Any
    body_raw: Optional[bytes]
    client: Dict[str, Optional[str]]
    session: Dict[str, Optional[str]]
    request_id: str


def _normalize_headers(headers: Mapping[str, str]) -> Dict[str, str]:
    return {key.title(): value for key, value in headers.items()}


async def build_request_context(
    request: Request,
    full_path: str,
    session: SessionContext,
) -> RequestContext:
    """Gather request details into a serialisable context."""

    raw_body = await request.body()
    body_json: Any = None

    if raw_body:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            try:
                body_json = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise SandboxExecutionError("Invalid JSON in request body", status_code=400) from exc

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    context: RequestContext = {
        "method": request.method,
        "path": f"/{full_path}".rstrip("/") or "/",
        "segments": [segment for segment in full_path.split("/") if segment],
        "query": {key: request.query_params.getlist(key) for key in request.query_params},
        "headers": _normalize_headers(dict(request.headers)),
        "body_json": body_json,
        "body_raw": raw_body or None,
        "client": {
            "ip": getattr(request.client, "host", None),
        },
        "session": {"id": session.id, "token": session.token},
        "request_id": request_id,
    }

    return context


sandbox_manager = SandboxManager()


async def handle_request(
    full_path: str,
    request: Request,
    session: SessionContext = Depends(session_dependency),
) -> Response:
    """Entry point for the catch-all FastAPI route."""

    ctx = await build_request_context(request, full_path, session)
    logger.info("request_received", extra={"request_id": ctx["request_id"], "session_id": session.id})

    try:
        sandbox_response: SandboxResponse = await sandbox_manager.execute_planned(ctx)
    except SandboxExecutionError:
        raise
    except Exception as exc:
        logger.exception("sandbox_execution_failure", extra={"request_id": ctx["request_id"]})
        raise SandboxExecutionError("Sandbox execution failed", status_code=500) from exc

    headers = sandbox_response.headers or {}
    headers.setdefault("X-Request-ID", ctx["request_id"])

    if sandbox_response.is_json:
        return JSONResponse(
            content=sandbox_response.body or None,
            status_code=sandbox_response.status,
            headers=headers,
        )

    return Response(
        content=sandbox_response.body or b"",
        media_type=sandbox_response.media_type,
        status_code=sandbox_response.status,
        headers=headers,
    )

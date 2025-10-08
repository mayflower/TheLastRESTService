"""Driver module executed inside the sandbox session."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .http_response import make_response
from .router import PlanningError, plan
from .safety import SafetyError, safe_exec
from .store import SessionStore


def _error_response(status: int, message: str, session_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": status,
        "headers": {"Content-Type": "application/json"},
        "body": {"error": message},
        "is_json": True,
        "session_state": session_state,
    }


def handle(ctx: Dict[str, Any], session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Entry point invoked by the host to service a request."""

    session_state = session_state or {}

    try:
        planning = plan(ctx)
    except PlanningError as exc:
        return _error_response(400, str(exc), session_state)

    code = planning.get("code")
    if not isinstance(code, str):
        return _error_response(500, "Planner did not return executable code", session_state)

    session_info = ctx.get("session") or {}
    tenant_id = session_info.get("id")
    if not tenant_id:
        return _error_response(400, "Missing session identifier", session_state)

    session_store = SessionStore(session_state, tenant_id)
    resource_store = session_store.resource(planning["resource"])

    exec_globals: Dict[str, Any] = {
        "ctx": ctx,
        "plan": planning,
        "store": resource_store,
        "session_store": session_store,
        "make_response": make_response,
    }
    exec_locals: Dict[str, Any] = {}

    try:
        safe_exec(code, exec_globals, exec_locals)
    except SafetyError as exc:
        return _error_response(400, f"Generated code rejected: {exc}", session_store.snapshot())
    except (ValueError, TypeError, KeyError) as exc:
        return _error_response(400, str(exc), session_store.snapshot())
    except Exception as exc:  # pragma: no cover - defensive
        return _error_response(500, f"Sandbox execution error: {exc}", session_store.snapshot())

    reply = exec_locals.get("REPLY") or exec_globals.get("REPLY")
    if not isinstance(reply, dict):
        return _error_response(500, "Sandbox plan did not produce a response", session_store.snapshot())

    headers = dict(reply.get("headers") or {})
    body = reply.get("body")
    media_type = reply.get("media_type")
    is_json = bool(reply.get("is_json", media_type is None))
    status = int(reply.get("status", 200))

    if is_json and body is not None and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    if not is_json and body is None and "Content-Type" in headers:
        headers.pop("Content-Type", None)

    return {
        "status": status,
        "headers": headers,
        "body": body,
        "media_type": media_type,
        "is_json": is_json,
        "session_state": session_store.snapshot(),
    }

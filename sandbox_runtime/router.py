"""Router and planner utilities executed within the sandbox."""

from __future__ import annotations

import textwrap
import re
from typing import Any, Dict, List, Optional

_SUPPORTED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_RESOURCE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class PlanningError(ValueError):
    """Raised when the router cannot derive a plan from the request context."""


def _validate_resource(segments: List[str]) -> str:
    if not segments:
        raise PlanningError("Resource path is required")
    resource = segments[0]
    if not resource:
        raise PlanningError("Resource name is empty")
    if not _RESOURCE_PATTERN.match(resource):
        raise PlanningError("Invalid resource name")
    return resource


def _determine_action(method: str, segments: List[str]) -> Dict[str, Any]:
    identifier: Optional[str] = None
    search = False

    if len(segments) >= 2:
        if segments[1] == "search":
            search = True
        else:
            identifier = segments[1]

    if method == "POST" and not identifier and not search:
        action = "create"
    elif method == "GET" and search:
        action = "search"
    elif method == "GET" and identifier:
        action = "retrieve"
    elif method == "GET" and not identifier:
        action = "list"
    elif method == "DELETE" and identifier:
        action = "delete"
    elif method == "PUT" and identifier:
        action = "replace"
    elif method == "PATCH" and identifier:
        action = "update"
    else:
        raise PlanningError("Unsupported combination of method and path")

    return {"action": action, "identifier": identifier, "search": search}


def _code_for_action(resource: str, action: str) -> str:
    prefix_literal = repr("/" + resource + "/")

    if action == "create":
        return textwrap.dedent(
            f"""
            body = ctx.get("body_json")
            if not isinstance(body, dict):
                raise ValueError("Expected JSON object body")
            record = store.insert(dict(body))
            location = {prefix_literal} + str(record["id"])
            headers = {{"Content-Type": "application/json", "Location": location}}
            REPLY = make_response(201, record, headers=headers)
            """
        )
    if action == "retrieve":
        return textwrap.dedent(
            """
            record = store.get(plan.get("identifier"))
            if record is None:
                REPLY = make_response(404, {"error": "not found"})
            else:
                REPLY = make_response(200, record)
            """
        )
    if action == "delete":
        return textwrap.dedent(
            """
            deleted = store.delete(plan.get("identifier"))
            if not deleted:
                REPLY = make_response(404, {"error": "not found"})
            else:
                REPLY = make_response(204, None, headers={}, is_json=False)
            """
        )
    if action == "replace":
        return textwrap.dedent(
            """
            body = ctx.get("body_json")
            if not isinstance(body, dict):
                raise ValueError("Expected JSON object body")
            record = store.replace(plan.get("identifier"), dict(body))
            if record is None:
                REPLY = make_response(404, {"error": "not found"})
            else:
                REPLY = make_response(200, record)
            """
        )
    if action == "update":
        return textwrap.dedent(
            """
            body = ctx.get("body_json")
            if not isinstance(body, dict):
                raise ValueError("Expected JSON object body")
            record = store.update(plan.get("identifier"), dict(body))
            if record is None:
                REPLY = make_response(404, {"error": "not found"})
            else:
                REPLY = make_response(200, record)
            """
        )
    if action == "list":
        return textwrap.dedent(
            """
            query = ctx.get("query") or {}
            raw_limit = (query.get("limit") or [None])[0]
            raw_offset = (query.get("offset") or [0])[0]
            raw_sort = (query.get("sort") or [None])[0]

            limit = int(raw_limit) if raw_limit not in (None, "") else None
            offset = int(raw_offset) if raw_offset not in (None, "") else 0

            items, total = store.list(limit=limit, offset=offset, sort=raw_sort)
            page = {
                "limit": limit if limit is not None else len(items),
                "offset": offset,
                "total": total,
            }
            REPLY = make_response(200, {"items": items, "page": page})
            """
        )
    if action == "search":
        return textwrap.dedent(
            """
            query = ctx.get("query") or {}
            criteria = {}
            for key, values in query.items():
                if not values:
                    continue
                if key in {"limit", "offset", "sort"}:
                    continue
                criteria[key] = values[-1]

            matches = list(store.search(criteria))
            REPLY = make_response(200, matches)
            """
        )

    raise PlanningError(f"Unsupported action: {action}")


def plan(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a plan skeleton for the incoming request."""

    method = (ctx.get("method") or "GET").upper()
    if method not in _SUPPORTED_METHODS:
        raise PlanningError("HTTP method not supported")

    segments = list(ctx.get("segments") or [])
    resource = _validate_resource(segments)
    action_info = _determine_action(method, segments)
    code = _code_for_action(resource, action_info["action"])

    return {
        "action": action_info["action"],
        "resource": resource,
        "identifier": action_info["identifier"],
        "search": action_info["search"],
        "code": code,
    }

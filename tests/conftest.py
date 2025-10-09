from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if TYPE_CHECKING:  # pragma: no cover - hints only
    from fastapi.testclient import TestClient


def _mock_llm_planner(prompt: str) -> str:
    """Mock LLM that generates plans based on request context."""
    # Extract JSON context from the prompt string

    # Try to extract the context JSON
    start_marker = "REQUEST CONTEXT:"
    end_marker = "**Now output"

    start_idx = prompt.find(start_marker)
    end_idx = prompt.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        # Fallback plan
        ctx = {"method": "GET", "segments": [], "query": {}}
    else:
        # Find the opening brace of the JSON
        ctx_section = prompt[start_idx + len(start_marker) : end_idx]
        json_start = ctx_section.find("{")
        if json_start == -1:
            ctx = {"method": "GET", "segments": [], "query": {}}
        else:
            ctx_str = ctx_section[json_start:].strip()
            try:
                ctx = json.loads(ctx_str)
            except json.JSONDecodeError:
                ctx = {"method": "GET", "segments": [], "query": {}}

    method = ctx.get("method", "GET")
    segments = ctx.get("segments", [])
    resource = segments[0] if segments else "unknown"
    identifier = segments[1] if len(segments) > 1 and segments[1] != "search" else None
    is_search = len(segments) > 1 and segments[1] == "search"

    # Determine action
    if method == "POST" and not identifier:
        action = "create"
        code = f"""body = ctx.get("body_json")
if not isinstance(body, dict):
    raise ValueError("Expected JSON object body")
record = store.insert(dict(body))
location = "/{resource}/" + str(record["id"])
headers = {{"Content-Type": "application/json", "Location": location}}
REPLY = make_response(201, record, headers=headers)"""
    elif method == "GET" and is_search:
        action = "search"
        code = """query = ctx.get("query") or {}
criteria = {}
for key, values in query.items():
    if not values:
        continue
    if key in {"limit", "offset", "sort"}:
        continue
    criteria[key] = values[-1]

matches = list(store.search(criteria))
REPLY = make_response(200, matches)"""
    elif method == "GET" and identifier:
        action = "get"
        code = """record = store.get(plan.get("identifier"))
if record is None:
    REPLY = make_response(404, {"error": "not found"})
else:
    REPLY = make_response(200, record)"""
    elif method == "GET" and not identifier:
        action = "list"
        code = """query = ctx.get("query") or {}
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
REPLY = make_response(200, {"items": items, "page": page})"""
    elif method == "DELETE" and identifier:
        action = "delete"
        code = """deleted = store.delete(plan.get("identifier"))
if not deleted:
    REPLY = make_response(404, {"error": "not found"})
else:
    REPLY = make_response(204, None, headers={}, is_json=False)"""
    elif method == "PUT" and identifier:
        action = "replace"
        code = """body = ctx.get("body_json")
if not isinstance(body, dict):
    raise ValueError("Expected JSON object body")
record = store.replace(plan.get("identifier"), dict(body))
if record is None:
    REPLY = make_response(404, {"error": "not found"})
else:
    REPLY = make_response(200, record)"""
    elif method == "PATCH" and identifier:
        action = "patch"
        code = """body = ctx.get("body_json")
if not isinstance(body, dict):
    raise ValueError("Expected JSON object body")
record = store.update(plan.get("identifier"), dict(body))
if record is None:
    REPLY = make_response(404, {"error": "not found"})
else:
    REPLY = make_response(200, record)"""
    else:
        action = "unknown"
        code = 'REPLY = make_response(400, {"error": "unsupported"})'

    plan = {
        "action": action,
        "resource": resource,
        "identifier": identifier,
        "criteria": {},
        "payload": ctx.get("body_json", {}),
        "response_hints": {},
        "code": {"language": "python", "block": f"```python\n{code}\n```"},
    }

    return json.dumps(plan, indent=2)


@pytest.fixture(autouse=True)
def mock_llm_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-mock LLM client for all tests."""
    # Use environment variable to enable mock mode
    # DISABLED: Using real LLM for tests since keys are available
    # monkeypatch.setenv("LLM_MOCK_HANDLER", "tests.conftest._mock_llm_planner")
    # monkeypatch.setenv("OPENAI_API_KEY", "test-key")


@pytest.fixture
def make_client(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, str] | None], TestClient]:
    """Factory fixture to build a TestClient with optional environment overrides."""

    def factory(env: dict[str, str] | None = None) -> TestClient:
        from app import api as app_api, config as app_config
        from app.main import create_app
        from app.sandbox import SandboxManager
        from fastapi.testclient import TestClient

        overrides = env or {}
        if "LARS_AUTH_TOKEN" in overrides:
            monkeypatch.setenv("LARS_AUTH_TOKEN", overrides["LARS_AUTH_TOKEN"])
        else:
            monkeypatch.delenv("LARS_AUTH_TOKEN", raising=False)

        app_config.get_settings.cache_clear()
        app_api.sandbox_manager = SandboxManager()

        app = create_app()
        return TestClient(app)

    return factory

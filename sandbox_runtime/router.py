"""Router and planner utilities executed within the sandbox."""

from __future__ import annotations

import json
import re
from typing import Any

from .llm_client import LLMClientError, call_llm


_RESOURCE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class PlanningError(ValueError):
    """Raised when the router cannot derive a plan from the request context."""


def _build_prompt(ctx: dict[str, Any], store: Any) -> str:
    """Build the LLM prompt from request context and learned schema."""

    # Create a serializable copy of context (exclude bytes)
    ctx_copy = {k: v for k, v in ctx.items() if k != "body_raw"}
    ctx_json = json.dumps(ctx_copy, indent=2)

    # Get learned schema if available
    schema_context = ""
    try:
        schema = store.get_schema()
        if schema:
            resource_name = ctx.get("segments", [])[0] if ctx.get("segments") else "resource"
            schema_context = f"""
**LEARNED SCHEMA for /{resource_name}:**
Previous operations created records with these fields: {", ".join(schema["fields"])}
Example record structure: {json.dumps(schema["example"], indent=2)}

IMPORTANT: Maintain this format for consistency across all operations.
When listing or retrieving records, ensure they include these fields.
"""
    except Exception:
        pass  # Schema is optional

    return f"""You are a REST Planner. Analyze the HTTP request and return ONLY a JSON object (no other text).
{schema_context}

The JSON MUST have these exact fields:
- "action": one of "create", "get", "list", "replace", "patch", "delete", or "search"
- "resource": the collection name (first path segment)
- "identifier": the ID from path (or null)
- "criteria": {{}} (empty object)
- "payload": the request body (or {{}})
- "response_hints": {{}}
- "code": {{"language": "python", "block": "```python\\n...\\n```"}}

**RESOURCESTORE API (use ONLY these methods):**
- `store.insert(obj: dict) -> dict` - Insert record, auto-generates ID if missing, returns record with ID
- `store.get(identifier) -> dict | None` - Get record by ID, returns None if not found
- `store.delete(identifier) -> bool` - Delete record, returns True if deleted, False if not found
- `store.replace(identifier, obj: dict) -> dict | None` - Replace entire record, returns None if not found
- `store.update(identifier, changes: dict) -> dict | None` - Merge changes into record, returns None if not found
- `store.list(limit=None, offset=0, sort=None) -> tuple[list[dict], int]` - Returns (items, total_count)
- `store.search(criteria: dict) -> list[dict]` - Filter records with suffixes: __contains, __icontains, __startswith, __endswith
- `store.get_schema() -> dict | None` - Get learned schema metadata (fields, example)

**SEARCH FILTER SUFFIXES:**
- Exact match: `{{"name": "Alice"}}` - name equals "Alice"
- Contains: `{{"name__contains": "Ali"}}` - name contains "Ali" (case-sensitive)
- Case-insensitive contains: `{{"name__icontains": "ali"}}` - name contains "ali" (case-insensitive)
- Starts with: `{{"name__startswith": "Ali"}}` - name starts with "Ali"
- Ends with: `{{"email__endswith": "@example.com"}}` - email ends with "@example.com"

**IMPORTANT:**
- When store methods return None, that means "not found" - return 404
- store.list() returns a TUPLE (items, total) - you MUST format this as {{"items": items, "page": {{...}}}}
- DO NOT invent methods like store.exists() - use store.get() which returns None if not found
- `make_response` signature: `make_response(status: int, body=None, headers=None)` (ONLY 3 args)

The code block must:
- Use `store` (ResourceStore API), `ctx` (request context), `plan`, and `make_response(status, body, headers)`
- Set a variable called `REPLY` using make_response()
- For POST /resource/ → `body = ctx.get("body_json"); rec = store.insert(body); REPLY = make_response(201, rec, {{"Location": f"/resource/{{rec['id']}}"}})`
- For GET /resource/<id> → get by plan["identifier"]; if None return 404, else return 200
- For DELETE /resource/<id> → delete; if False return 404, else return `make_response(204, None, {{}})`
- For PUT /resource/<id> → replace; if None return 404, else return 200
- For PATCH /resource/<id> → update; if None return 404, else return 200
- For GET /resource/ → list with pagination; MUST format as {{"items": items, "page": {{"total": total, "limit": ..., "offset": ...}}}}
- For GET /resource/search?key=val → search with query params; return list directly

IMPORTANT: In the "block" field, write the Python code directly WITHOUT any markdown fencing (no ``` or ```python). Just the raw Python code.

**SCHEMA:**

```json
{{
  "action": "create|get|list|replace|patch|delete|search",
  "resource": "<collection name>",
  "identifier": null,
  "criteria": {{}},
  "payload": {{}},
  "response_hints": {{}},
  "code": {{
    "language": "python",
    "block": "REPLY = make_response(200, {{}})"
  }}
}}
```

**Rules:**

* Collection name defaults to the first path segment (e.g., `/members/...` → `"members"`).
* `identifier` is the second segment if present and not a search keyword.
* Search operations can be named: `/search`, `/find`, `/query`, `/filter` - all mean action: "search".
* Query params with patterns like `findBy*`, `getBy*`, `searchBy*` also indicate search intent.
* Wildcards in query values: `name=Hart*` (prefix), `email=*@example.com` (suffix), `name=*oh*` (contains).
* `POST /<collection>/` → `action: "create"`.
* `GET /<collection>/` → `action: "list"`.
* `GET /<collection>/<id>` → `action: "get"`.
* `PUT /<collection>/<id>` → `action: "replace"`.
* `PATCH /<collection>/<id>` → `action: "patch"`.
* `DELETE /<collection>/<id>` → `action: "delete"`.
* If body lacks an `id` on create, the code should call `store.insert(payload)` and use the returned id.
* Your code must use **only** the provided `store` object, `ctx`, `plan`, and `make_response` function. Return a **Python dict** assigned to variable `REPLY` with structure: `{{"status": int, "body": <obj>, "headers": {{}}, "is_json": bool}}`. Do not print; just assign to REPLY.

**Examples:**

* `POST /members/` with body `{{"name": "Alice"}}` → insert into members, 201, `Location: /members/{{id}}`, return object with id.
* `GET /members/1` → return object or 404.
* `DELETE /members/1` → 204.
* `GET /members/search?name=hartmann` → `store.search({{"name": "hartmann"}})` - exact match.
* `GET /users/find?name=Hart*` → `store.search({{"name__startswith": "Hart"}})` - prefix wildcard.
* `GET /users/query?email=*@example.com` → `store.search({{"email__endswith": "@example.com"}})` - suffix wildcard.
* `GET /products/filter?name=*widget*` → `store.search({{"name__icontains": "widget"}})` - contains wildcard (case-insensitive).
* `GET /users/?getByFirstName=Johann` → `store.search({{"firstName": "Johann"}})` - query param style search.
* `GET /orders/?findByStatus=pending` → `store.search({{"status": "pending"}})` - alternative query param pattern.

**REQUEST CONTEXT:**

{ctx_json}

**Now output only the JSON object per the schema above. Ensure the "code" field contains a single fenced Python code block that assigns REPLY.**"""


def _extract_code_from_plan(plan_obj: dict[str, Any]) -> str:
    """Extract the Python code block from the LLM plan."""

    code_section = plan_obj.get("code")
    if not isinstance(code_section, dict):
        raise PlanningError("Plan missing 'code' section")

    block = code_section.get("block", "")
    if not isinstance(block, str):
        raise PlanningError("Code block is not a string")

    # Remove any markdown fencing if present (though we asked LLM not to include it)
    code = block.strip()
    if code.startswith("```python"):
        code = code[len("```python") :].strip()
    elif code.startswith("```"):
        code = code[3:].strip()

    if code.endswith("```"):
        code = code[:-3].strip()

    return code


def plan(ctx: dict[str, Any], store: Any) -> dict[str, Any]:
    """Produce a plan by calling the LLM with the request context and schema."""

    method = (ctx.get("method") or "GET").upper()
    segments = list(ctx.get("segments") or [])

    # Validate resource name
    if not segments:
        raise PlanningError("Resource path is required")
    resource = segments[0]
    if not resource:
        raise PlanningError("Resource name is empty")
    if not _RESOURCE_PATTERN.match(resource):
        raise PlanningError("Invalid resource name")

    # Build prompt with schema context and call LLM
    prompt = _build_prompt(ctx, store)

    try:
        llm_response = call_llm(prompt)
    except LLMClientError as exc:
        raise PlanningError(f"LLM call failed: {exc}") from exc

    # Parse JSON response
    # LLM might wrap in markdown, extract JSON
    response_text = llm_response.strip()

    # Try to extract JSON from markdown fence
    original_response = response_text
    if "```json" in response_text:
        start = response_text.find("```json") + len("```json")
        end = response_text.find("```", start)
        if end != -1:
            response_text = response_text[start:end].strip()
    elif "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        if end != -1:
            response_text = response_text[start:end].strip()

    # If the response_text is still empty or doesn't look like JSON, use original
    if not response_text or not response_text.startswith("{"):
        response_text = original_response

    try:
        plan_obj = json.loads(response_text)
    except json.JSONDecodeError as exc:
        # Try to find JSON object in the response

        # Just use the original response and let it fail properly
        raise PlanningError(
            f"LLM returned invalid JSON: {exc}. Response: {response_text[:1000]}"
        ) from exc

    if not isinstance(plan_obj, dict):
        raise PlanningError("LLM response is not a JSON object")

    # Extract and validate required fields
    action = plan_obj.get("action")
    resource_from_plan = plan_obj.get("resource", resource)
    identifier = plan_obj.get("identifier")

    if not action:
        raise PlanningError(f"Plan missing 'action' field. Keys present: {list(plan_obj.keys())}")

    # Extract code
    code = _extract_code_from_plan(plan_obj)

    return {
        "action": action,
        "resource": resource_from_plan,
        "identifier": identifier,
        "search": plan_obj.get("search", False),
        "code": code,
    }

**Title:** Dynamic REST metaservice where the LLM interprets each request and emits/executes code inside a sandbox (FastAPI + Pyodide/Deno)

### Objective

Implement a production‑minded HTTP service with **no fixed endpoints**. All routes are handled by a single **catch‑all** FastAPI path. For each request:

1. Gather full request context (method, path, query, headers, body).
2. Send that context into a **stateful LangChain Sandbox (Pyodide + Deno)** session.
3. Inside the sandbox, call an **LLM Planner** that:

   * Interprets the REST intent from the request (e.g., `POST /members/`, `GET /members/1`, `DELETE /members/2`, `GET /members/search?name=hartmann`).
   * **Generates minimal Python code** to perform the action **in the sandbox filesystem** (e.g., read/write `members.json` under `/data`).
   * Executes the generated code in the same sandbox session.
4. Return a **REST‑style response** (status code, headers, body) derived from the sandbox execution result.

> **Key principle:** The API process **never `exec`/`eval`s** user or LLM‑generated code. **All code runs only inside the sandbox**. The LLM call that produces code also occurs **inside the sandbox** (the sandbox has allowlisted network access to the chosen LLM provider).

---

## Acceptance Criteria

1. **No predeclared resources.** Only one catch‑all route handles `GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD` for `/{path:path}`.
2. **Stateful sandbox sessions.** Each request is bound to a tenant/session (e.g., header `X-Session-ID` or derived from API key). Session state persists via `session_bytes/session_metadata`—treated as **opaque** by the API.
3. **LLM-in-sandbox planning.** For each request, the sandbox:

   * Builds a compact `ctx` object from method, path, query, headers, and body.
   * Calls an LLM **Router+Planner** prompt to output a **strict JSON plan** + a **single Python code block**.
   * Executes only that code after safety checks (AST allowlist), using a **`ResourceStore`** helper that confines file I/O to `/data/<tenant>/`.
4. **Resource storage is in JSON files inside the sandbox** (e.g., `members.json`, `orders.json`). Create files on first use. IDs auto‑assign if absent. Prefer integer IDs for readability; accept strings if client supplies one.
5. **REST semantics, dynamically inferred.** Examples that must work *without predefining endpoints*:

   * `POST /members/` (body JSON) → append, assign ID, 201 Created, `Location: /members/{id}`, return created object.
   * `GET /members/1` → return object or 404.
   * `DELETE /members/1` → remove, return 204 No Content.
   * `GET /members/search?name=hartmann` → filter `members.json` for `name == "hartmann"`, return list.
   * `PUT /members/1` → replace; `PATCH /members/1` → partial update.
   * `GET /members/` → list with `?limit&offset&sort` support (best‑effort).
6. **Security boundaries.**

   * API process never runs untrusted code.
   * Sandbox execution is time‑boxed and memory‑capped.
   * Outbound network from sandbox code is **denied by default**; **only** the LLM planner is allowed to reach the configured provider host(s). Resource‑operation code must not call the network.
   * Generated code is AST‑checked to allow only safe modules/ops (see “Safety policy” below).
7. **Observability.** Log request ID, latency, sandbox status, and minimal traces (redact secrets). Expose `/healthz`.
8. **OpenAPI docs.** `/docs` and `/redoc` should explain the catch‑all design and show examples.
9. **Tests.** E2E tests cover the example flows above, deny‑net enforcement, and state persistence across calls.

---

## High‑Level Design

### 1) API Layer (FastAPI)

* **Catch‑all route**

  ```python
  app.add_api_route(
      "/{full_path:path}",
      handle_request,
      methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"]
  )
  ```
* `handle_request` builds:

  ```python
  RequestContext = {
    "method": <str>,
    "path": "/"+full_path,           # original path
    "segments": <list[str]>,         # split by "/"
    "query": <dict[str, list[str]]>,
    "headers": <dict[str,str]>,      # sanitized
    "body_json": <obj or None>,
    "body_raw": <bytes if not json>,
    "client": {"ip": "..."},
    "session": {"id": <tenant_or_key>}
  }
  ```
* Pass `RequestContext` to `SandboxManager.execute_planned(ctx)` and return its `HTTPResponse`.

### 2) Sandbox Manager (outside‑sandbox glue)

* Maintains **stateful** `PyodideSandbox` sessions keyed by `session.id`.
* For each request:

  1. Push `ctx` into sandbox (`json` → base64 string).
  2. Run the **sandbox driver** function (`driver.handle(ctx)`), which:

     * Calls the **LLM Router+Planner** inside the sandbox.
     * Validates plan schema.
     * Verifies the generated code AST against allowlist.
     * Executes the code in the same session with access to `ResourceStore`.
     * Returns a structured `HTTPResponse`:

       ```python
       {"status": 200, "headers": {"Content-Type":"application/json"}, "body": <json-serializable>}
       ```
* Persist updated `session_bytes`/`session_metadata` on each call (never deserialize them in the API).

### 3) Sandbox Runtime (inside Pyodide)

Preload these modules/files inside the sandbox session on first use:

* **`driver.py`** — entrypoint with `handle(ctx)`:

  * `plan = router_plan(ctx)` → strict JSON (action, resource, id, criteria, payload, code).
  * `code = plan["code"]["python"]` (single block).
  * `assert_safe(code)` → AST gate.
  * `result = exec_in_restricted_env(code, store=ResourceStore(tenant), ctx=ctx)`
  * `return to_http_response(plan, result)`
* **`router.py`** — the LLM Router+Planner:

  * Prompt template (below) + call to provider (OpenAI/Anthropic/etc.) using sandbox‑scoped API key from env.
  * Output must be JSON with a single fenced `python code block`.
* **`store.py`** — `ResourceStore` abstraction with safe I/O:

  * Base dir: `/data/{tenant}/`.
  * File per collection: `/data/{tenant}/{collection}.json`.
  * Methods: `get_all`, `get(id)`, `insert(obj) -> id`, `replace(id, obj)`, `patch(id, delta)`, `delete(id)`, `search(filters)`.
  * Guarantees: create‑on‑first‑use, atomic write (write temp file then rename), simple integer autoincrement if `id` missing.
* **`safety.py`** — AST allowlist & sandbox env:

  * Allowed imports: `json`, `re`, `math`, `statistics`, `uuid`, `datetime`, `itertools`, `typing`, `pathlib`, `os` (guarded), `io`.
  * **No** `subprocess`, `socket`, `sys` mutation, `ctypes`, `eval`, `exec`, `importlib`, file writes outside `/data/{tenant}`.
  * Provide guarded `open` that rejects paths outside the tenant dir; expose to generated code as `safe_open`.
* **`http_response.py`** — helpers to map actions to HTTP codes and `Location` headers (`POST` → 201, etc.).

---

## The Router+Planner Prompt (runs **inside** the sandbox)

Use this exact prompt (the agent may tune wording but must keep schema and constraints):

> **SYSTEM (inside sandbox):**
> You are a REST Planner. For each HTTP request context, you must infer the intended CRUD/search action over a resource collection and produce:
>
> 1. a **strict JSON plan** and
> 2. a **single Python code block** that performs the action using the provided `ResourceStore` API (already available in the runtime).
>    You do **not** make network calls in the generated code. You only read/write JSON collections via `store`. You never import disallowed modules. You return data structures that are JSON‑serializable.

> **SCHEMA (your output must be valid JSON):**
>
> ````json
> {
>   "action": "create|get|list|replace|patch|delete|search",
>   "resource": "<collection name>",          // e.g. "members"
>   "id": "<string or int or null>",          // for /{id}
>   "criteria": { "field": "value", ... },    // for search/filter/list
>   "payload": { ... },                        // request body if any
>   "response_hints": {                       // optional: status overrides, headers
>     "status": 200,
>     "location_id": "<id if created>"
>   },
>   "code": {
>     "language": "python",
>     "block": "```python\\n# code that uses 'store' and 'ctx'\\n...\\n```"
>   }
> }
> ````
>
> **Rules:**
>
> * Collection name defaults to the first path segment (e.g., `/members/...` → `"members"`).
> * `id` is the second segment if present and not `"search"`.
> * `/.../search` should set `action: "search"`; parse filters from query params.
> * `POST /<collection>/` → `action: "create"`.
> * `GET /<collection>/` → `action: "list"`.
> * `GET /<collection>/<id>` → `action: "get"`.
> * `PUT /<collection>/<id>` → `action: "replace"`.
> * `PATCH /<collection>/<id>` → `action: "patch"`.
> * `DELETE /<collection>/<id>` → `action: "delete"`.
> * If body lacks an `id` on create, the code should ask `store.insert(payload)` and use the returned id.
> * Your code must use **only** the provided `store` object and `ctx` and return a **Python dict** `{ "status": int, "body": <obj>, "headers": { ... } }`. Do not print; just return.
>
> **Examples:**
>
> * `POST /members/` with body `{ "name": "Alice" }` → insert into `members.json`, 201, `Location: /members/{id}`, return object with `id`.
> * `GET /members/1` → return object or 404.
> * `DELETE /members/1` → 204.
> * `GET /members/search?name=hartmann` → filter all where `name == "hartmann"`.
>
> **Now output only the JSON object per the schema above.**

---

## Code Contract for Generated Snippets

* The router emits **one** fenced Python block that will be extracted and executed with:

  ```python
  result = run_user_code(
      code_block,
      env={"store": ResourceStore(tenant), "ctx": ctx}
  )
  ```
* The block must end by assigning a **variable named `REPLY`**:

  ```python
  # REQUIRED in generated code
  REPLY = {
      "status": 200,
      "headers": {"Content-Type": "application/json"},
      "body": <json-serializable>
  }
  ```
* Typical patterns (the router should generate these):

  **Create**

  ```python
  obj = dict(ctx.get("body_json") or {})
  new_id = store.insert(obj)            # sets obj["id"] if not present
  REPLY = {
      "status": 201,
      "headers": {"Location": f"/members/{new_id}"},
      "body": obj
  }
  ```

  **Get**

  ```python
  rid = ctx["segments"][1]
  obj = store.get(rid)
  REPLY = {"status": 200, "body": obj} if obj is not None else {"status": 404, "body": {"error":"not found"}}
  ```

  **Search**

  ```python
  q = ctx["query"]
  name = (q.get("name") or [None])[0]
  matches = store.search({"name": name}) if name is not None else []
  REPLY = {"status": 200, "body": matches}
  ```

---

## Safety Policy (enforced inside sandbox before exec)

* **AST allowlist**: permit literals, assignments, dict/list/set/tuple, calls, attribute access, control flow, comprehensions; **deny** `Import`, `Global`, `Nonlocal`, `Lambda`, `With`, `Try` catching broad exceptions that swallow policy, `Exec`, `Eval`.
* **Module guard**: only allow imports from `json`, `re`, `math`, `statistics`, `uuid`, `datetime`, `itertools`, `typing`, `pathlib`, `os` (guarded), `io`. Reject everything else.
* **I/O guard**: expose `safe_open` and `ResourceStore` which confine access to `/data/{tenant}`; file open attempts outside this subtree raise.
* **No network** in generated code. The planner itself may call the LLM provider (allowlist only those hosts).
* **Time & memory limits**: per‑exec timeout (e.g., 5–10s) and output truncation (stdout/stderr/result size caps).
* **Secrets**: The only secrets in sandbox env are those required for the planner (LLM key). Never return or log them.

---

## Configuration

* `AUTH_TOKEN` for simple bearer auth to the API.
* `SANDBOX_DENY_NET=true`
* `SANDBOX_LLM_ALLOWED_HOSTS="api.openai.com,api.anthropic.com"` (planner only)
* `DEFAULT_PROVIDER=openai|anthropic` with minimal client inside sandbox (`httpx`).
* `MAX_EXEC_MS`, `MAX_RESULT_BYTES`, `MAX_STDOUT_BYTES`.

---

## Minimal Examples to Verify

1. **Create → Get**

   * `POST /members/` `{ "name": "Alice" }` → `201`, `Location: /members/1`, body `{ "id": 1, "name": "Alice" }`
   * `GET /members/1` → `200`, body `{ "id": 1, "name": "Alice" }`

2. **Search**

   * `GET /members/search?name=hartmann` → `200`, body `[ { "id": 2, "name": "hartmann", ...}, ... ]`

3. **Delete**

   * `DELETE /members/1` → `204`
   * `GET /members/1` → `404`

4. **List with paging**

   * `GET /members/?limit=10&offset=20` → `200`, body `{ "items":[...], "page":{"limit":10,"offset":20,"total":N} }`

---

## Files to Implement

```
app/
  main.py           # create FastAPI app, mount catch-all route, auth, CORS
  api.py            # handle_request(): build ctx, call SandboxManager
  sandbox.py        # SandboxManager: stateful PyodideSandbox + execute_planned(ctx)
  config.py         # env settings (auth, timeouts, providers, allowlists)
  security.py       # bearer auth dependency
  logging.py        # JSON logging with request_id
  errors.py         # error envelopes & exception handlers

sandbox_runtime/    # pushed into sandbox session on first use
  driver.py         # handle(ctx) → plan → validate → execute → HTTPResponse
  router.py         # LLM call + prompt (above) → plan JSON + fenced code
  store.py          # ResourceStore (JSON files, atomic writes, autoincrement)
  safety.py         # AST allowlist, open/file guard, exec wrapper
  http_response.py  # helpers mapping actions to HTTP responses

tests/
  test_create_get_delete.py
  test_search.py
  test_paging.py
  test_security.py
  test_statefulness.py

infra/
  Dockerfile        # includes Python + Deno, installs langchain-sandbox
  Makefile          # dev, test, run
  README.md         # quickstart, examples, API usage
```

---

## Hints for the Agent

* Use `app.add_api_route("/{full_path:path}", ...)` to avoid defining any fixed endpoints.
* In the sandbox, keep a global `__BOOTSTRAPPED` flag; on first call, load `driver.py`, `router.py`, `store.py`, `safety.py`.
* For JSON files, implement **atomic writes** (write to `tmp` then `os.replace`).
* When assigning IDs, track the **max existing ID** in the file and increment; if client supplies a string ID, accept it unmodified.
* Make `search` support exact‑match and simple contains (`?name__contains=hart`) to be helpful.
* Return proper REST codes: `201` + `Location` on create, `200` on read/search/list, `204` on delete, `404` on missing resource, `400` on malformed input.

---

### Done =

* You can `POST /members/` with `{ "name": "Alice" }` and immediately `GET /members/1` from the sandbox‑persisted JSON.
* You can `GET /members/search?name=hartmann` and get filtered results.
* **No fixed endpoints were coded.** All behavior is decided at runtime by the LLM inside the sandbox.
* API never executes untrusted code; only the sandbox does.



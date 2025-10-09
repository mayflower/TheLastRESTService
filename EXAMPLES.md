# Examples

This document provides detailed examples showing how to use LARS and how it works internally.

## Table of Contents

- [Quick Start Examples](#quick-start-examples)
- [How It Works: Step-by-Step Walkthrough](#how-it-works-step-by-step-walkthrough)
- [Complete Scenarios](#complete-scenarios)
- [Advanced Examples](#advanced-examples)

## Quick Start Examples

### Example 1: Creating a Resource

```bash
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "price": 1299.99, "stock": 15}'
```

**Response (201 Created):**
```json
{
  "id": "1",
  "name": "Laptop",
  "price": 1299.99,
  "stock": 15
}
```

**Response Headers:**
```
Location: /products/1
Content-Type: application/json
```

### Example 2: Retrieving a Resource

```bash
curl http://localhost:8000/products/1
```

**Response (200 OK):**
```json
{
  "id": "1",
  "name": "Laptop",
  "price": 1299.99,
  "stock": 15
}
```

### Example 3: Listing Resources

```bash
curl http://localhost:8000/products?limit=10&offset=0
```

**Response (200 OK):**
```json
{
  "items": [
    {"id": "1", "name": "Laptop", "price": 1299.99, "stock": 15},
    {"id": "2", "name": "Mouse", "price": 29.99, "stock": 100}
  ],
  "page": {
    "limit": 10,
    "offset": 0,
    "total": 2
  }
}
```

### Example 4: Searching Resources

```bash
curl "http://localhost:8000/products/search?name=Laptop"
```

**Response (200 OK):**
```json
[
  {"id": "1", "name": "Laptop", "price": 1299.99, "stock": 15}
]
```

### Example 5: Updating a Resource

```bash
curl -X PATCH http://localhost:8000/products/1 \
  -H "Content-Type: application/json" \
  -d '{"stock": 10}'
```

**Response (200 OK):**
```json
{
  "id": "1",
  "name": "Laptop",
  "price": 1299.99,
  "stock": 10
}
```

### Example 6: Replacing a Resource

```bash
curl -X PUT http://localhost:8000/products/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Gaming Laptop", "price": 1599.99, "stock": 8}'
```

**Response (200 OK):**
```json
{
  "id": "1",
  "name": "Gaming Laptop",
  "price": 1599.99,
  "stock": 8
}
```

### Example 7: Deleting a Resource

```bash
curl -X DELETE http://localhost:8000/products/1
```

**Response (204 No Content):**
(Empty body)

---

## How It Works: Step-by-Step Walkthrough

Let's trace what happens when you make a request to create a product.

### Request

```bash
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "price": 1299.99}'
```

### Step 1: Request Context Building

FastAPI receives the request and `app/api.py` builds a context dictionary:

```python
{
  "method": "POST",
  "path": "/products",
  "segments": ["products"],
  "query": {},
  "headers": {
    "Content-Type": "application/json",
    "Host": "localhost:8000"
  },
  "body_json": {
    "name": "Laptop",
    "price": 1299.99
  },
  "client": {"ip": "127.0.0.1"},
  "session": {"id": "sess_abc123", "token": "..."},
  "request_id": "req_xyz789"
}
```

### Step 2: LLM Prompt Construction

The sandbox's `router.py` builds a detailed prompt:

```
You are a REST Planner. Analyze the HTTP request and return ONLY a JSON object (no other text).

The JSON MUST have these exact fields:
- "action": one of "create", "get", "list", "replace", "patch", "delete", or "search"
- "resource": the collection name (first path segment)
- "identifier": the ID from path (or null)
- "criteria": {} (empty object)
- "payload": the request body (or {})
- "response_hints": {}
- "code": {"language": "python", "block": "..."}

The code block must:
- Use `store` (ResourceStore API), `ctx` (request context), `plan`, and `make_response(status, body, headers)`
- Set a variable called `REPLY` using make_response()
- `make_response` signature: `make_response(status: int, body=None, headers=None)` (ONLY these 3 args)
- For POST /resource/ → `body = ctx.get("body_json"); rec = store.insert(body); REPLY = make_response(201, rec, {"Location": f"/resource/{rec['id']}"})`

**REQUEST CONTEXT:**

{
  "method": "POST",
  "path": "/products",
  "segments": ["products"],
  "body_json": {
    "name": "Laptop",
    "price": 1299.99
  },
  ...
}

**Now output only the JSON object per the schema above.**
```

### Step 3: LLM Response

The LLM (OpenAI or Anthropic) analyzes the request and returns:

```json
{
  "action": "create",
  "resource": "products",
  "identifier": null,
  "criteria": {},
  "payload": {
    "name": "Laptop",
    "price": 1299.99
  },
  "response_hints": {},
  "code": {
    "language": "python",
    "block": "body = ctx.get(\"body_json\")\nif not isinstance(body, dict):\n    raise ValueError(\"Expected JSON object body\")\nrecord = store.insert(dict(body))\nlocation = f\"/products/{record['id']}\"\nheaders = {\"Content-Type\": \"application/json\", \"Location\": location}\nREPLY = make_response(201, record, headers=headers)"
  }
}
```

### Step 4: Code Extraction

The `router.py` extracts the Python code from the plan:

```python
body = ctx.get("body_json")
if not isinstance(body, dict):
    raise ValueError("Expected JSON object body")
record = store.insert(dict(body))
location = f"/products/{record['id']}"
headers = {"Content-Type": "application/json", "Location": location}
REPLY = make_response(201, record, headers=headers)
```

### Step 5: AST Validation

The sandbox's `safety.py` validates the code:

1. Parse into AST
2. Check each node against allowlist (no imports, no file I/O, etc.)
3. Reject any disallowed constructs
4. Allow the code to proceed

**Allowed nodes include:** assignments, function calls, comparisons, f-strings, loops, conditionals
**Disallowed nodes include:** imports, lambdas, class/function definitions, file operations

### Step 6: Code Execution

The sandbox executes the validated code:

```python
# Available in execution context:
# - store: ResourceStore instance for this session
# - ctx: Request context dict
# - plan: Plan object from LLM
# - make_response: Function to build response

# Execution happens in restricted namespace:
sandbox_globals = {
    "__builtins__": {
        "len": len, "range": range, "dict": dict,
        "str": str, "int": int, ...
    },
    "store": <ResourceStore>,
    "ctx": <RequestContext>,
    "plan": <Plan>,
    "make_response": <function>
}

exec(compiled_code, sandbox_globals, sandbox_locals)

# After execution:
# sandbox_locals["REPLY"] = {
#     "status": 201,
#     "body": {"id": "1", "name": "Laptop", "price": 1299.99},
#     "headers": {"Content-Type": "application/json", "Location": "/products/1"},
#     "is_json": True
# }
```

### Step 7: Storage Update

During execution, `store.insert()` is called:

1. Generates ID: `"1"`
2. Adds ID to record: `{"id": "1", "name": "Laptop", "price": 1299.99}`
3. Stores in memory: `self._data["products"]["1"] = {...}`
4. Persists to JSON file: `data/sessions/sess_abc123.json`
5. Returns the record with ID

**File contents after insert:**
```json
{
  "products": {
    "1": {
      "id": "1",
      "name": "Laptop",
      "price": 1299.99
    }
  }
}
```

### Step 8: Response Construction

The API process receives the sandbox response and builds the HTTP response:

```python
# Sandbox returned:
{
    "status": 201,
    "body": {"id": "1", "name": "Laptop", "price": 1299.99},
    "headers": {"Location": "/products/1"},
    "is_json": True
}

# FastAPI sends:
HTTP/1.1 201 Created
Content-Type: application/json
Location: /products/1
X-Request-ID: req_xyz789

{
  "id": "1",
  "name": "Laptop",
  "price": 1299.99
}
```

---

## Complete Scenarios

### Scenario 1: Building a Blog API

#### Create a Blog Post

```bash
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Getting Started with LARS",
    "author": "Alice",
    "content": "LARS is a dynamic REST API powered by LLMs...",
    "tags": ["tutorial", "rest", "llm"]
  }'
```

**Response:**
```json
{
  "id": "1",
  "title": "Getting Started with LARS",
  "author": "Alice",
  "content": "LARS is a dynamic REST API powered by LLMs...",
  "tags": ["tutorial", "rest", "llm"]
}
```

#### Add a Comment

```bash
curl -X POST http://localhost:8000/comments \
  -H "Content-Type: application/json" \
  -d '{
    "post_id": "1",
    "author": "Bob",
    "text": "Great article!"
  }'
```

**Response:**
```json
{
  "id": "1",
  "post_id": "1",
  "author": "Bob",
  "text": "Great article!"
}
```

#### Search Posts by Tag

```bash
curl "http://localhost:8000/posts/search?author=Alice"
```

**Response:**
```json
[
  {
    "id": "1",
    "title": "Getting Started with LARS",
    "author": "Alice",
    "content": "LARS is a dynamic REST API powered by LLMs...",
    "tags": ["tutorial", "rest", "llm"]
  }
]
```

### Scenario 2: E-Commerce Inventory

#### Add Products

```bash
# Add laptop
curl -X POST http://localhost:8000/inventory \
  -H "Content-Type: application/json" \
  -d '{"sku": "LAP-001", "name": "Gaming Laptop", "quantity": 5, "price": 1599.99}'

# Add mouse
curl -X POST http://localhost:8000/inventory \
  -H "Content-Type: application/json" \
  -d '{"sku": "MOU-001", "name": "Wireless Mouse", "quantity": 50, "price": 29.99}'
```

#### Check Stock

```bash
curl "http://localhost:8000/inventory/search?sku=LAP-001"
```

**Response:**
```json
[
  {
    "id": "1",
    "sku": "LAP-001",
    "name": "Gaming Laptop",
    "quantity": 5,
    "price": 1599.99
  }
]
```

#### Update Quantity (After Sale)

```bash
curl -X PATCH http://localhost:8000/inventory/1 \
  -H "Content-Type: application/json" \
  -d '{"quantity": 4}'
```

**Response:**
```json
{
  "id": "1",
  "sku": "LAP-001",
  "name": "Gaming Laptop",
  "quantity": 4,
  "price": 1599.99
}
```

### Scenario 3: Task Management

#### Create Project

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Website Redesign",
    "status": "active",
    "owner": "alice@example.com"
  }'
```

#### Add Tasks

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "1",
    "title": "Design mockups",
    "assignee": "bob@example.com",
    "status": "todo",
    "priority": "high"
  }'

curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "1",
    "title": "Implement header component",
    "assignee": "carol@example.com",
    "status": "in_progress",
    "priority": "medium"
  }'
```

#### List All Tasks

```bash
curl "http://localhost:8000/tasks?limit=20"
```

**Response:**
```json
{
  "items": [
    {
      "id": "1",
      "project_id": "1",
      "title": "Design mockups",
      "assignee": "bob@example.com",
      "status": "todo",
      "priority": "high"
    },
    {
      "id": "2",
      "project_id": "1",
      "title": "Implement header component",
      "assignee": "carol@example.com",
      "status": "in_progress",
      "priority": "medium"
    }
  ],
  "page": {
    "limit": 20,
    "offset": 0,
    "total": 2
  }
}
```

#### Search High Priority Tasks

```bash
curl "http://localhost:8000/tasks/search?priority=high"
```

**Response:**
```json
[
  {
    "id": "1",
    "project_id": "1",
    "title": "Design mockups",
    "assignee": "bob@example.com",
    "status": "todo",
    "priority": "high"
  }
]
```

---

## Advanced Examples

### Pagination

```bash
# Get first page (10 items)
curl "http://localhost:8000/products?limit=10&offset=0"

# Get second page
curl "http://localhost:8000/products?limit=10&offset=10"

# Get all items (no limit)
curl "http://localhost:8000/products"
```

### Complex Search Criteria

```bash
# Search by multiple fields
curl "http://localhost:8000/products/search?category=electronics&price_min=100"
```

**Note:** The LLM will interpret natural search parameters. For more complex queries, the generated code might include comparisons:

```python
# LLM might generate code like:
query = ctx.get("query") or {}
criteria = {}
for key, values in query.items():
    if key == "price_min":
        # LLM could generate comparison logic
        continue
    criteria[key] = values[-1] if values else None

matches = []
for item in store.list()[0]:
    if all(item.get(k) == v for k, v in criteria.items() if v):
        if "price_min" in query:
            price_min = int(query["price_min"][0])
            if item.get("price", 0) >= price_min:
                matches.append(item)
        else:
            matches.append(item)

REPLY = make_response(200, matches)
```

### Error Handling

#### Resource Not Found

```bash
curl http://localhost:8000/products/999
```

**Response (404 Not Found):**
```json
{
  "error": "not found"
}
```

#### Invalid JSON

```bash
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -d '{invalid json}'
```

**Response (400 Bad Request):**
```json
{
  "detail": "Invalid JSON in request body"
}
```

### Session Isolation

Each session has isolated storage:

**Session A:**
```bash
curl -X POST http://localhost:8000/notes \
  -H "X-Session-Token: session-a-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "Session A note"}'

curl http://localhost:8000/notes \
  -H "X-Session-Token: session-a-token"
# Returns: [{"id": "1", "text": "Session A note"}]
```

**Session B:**
```bash
curl http://localhost:8000/notes \
  -H "X-Session-Token: session-b-token"
# Returns: {"items": [], "page": {...}}  (empty - different session)
```

### Authentication Example

With authentication enabled:

```bash
# Without token (rejected)
curl http://localhost:8000/products
# Response: 401 Unauthorized

# With valid token
curl http://localhost:8000/products \
  -H "Authorization: Bearer your-secret-token"
# Response: 200 OK with data
```

---

## Understanding LLM Variability

The LLM interprets requests dynamically, which means:

1. **Same request, different code:** Two identical POST requests might generate slightly different Python code, but both will work correctly.

2. **Adaptive behavior:** The LLM can handle variations in request structure:
   ```bash
   # Both of these work:
   curl -X POST http://localhost:8000/users -d '{"name": "Alice"}'
   curl -X POST http://localhost:8000/user -d '{"username": "Alice"}'
   ```

3. **Natural language in paths:** The LLM can interpret semantic variations:
   ```bash
   # These might be interpreted similarly:
   GET /products/search?name=Laptop
   GET /products/find?name=Laptop
   GET /products/query?name=Laptop
   ```

## Debugging Tips

### View LLM Prompts

Set logging to DEBUG to see the prompts sent to the LLM:

```python
# In your environment or config
import logging
logging.getLogger("sandbox_runtime.router").setLevel(logging.DEBUG)
```

### Inspect Generated Code

The sandbox logs the generated code before execution. Check logs for:

```
[sandbox_runtime.runtime] Executing plan code for action=create
```

### Test Without LLM

Use the mock mode in tests:

```python
export LLM_MOCK_HANDLER="tests.conftest._mock_llm_planner"
pytest tests/
```

This uses deterministic code generation for predictable testing.

---

## Summary

LARS provides a unique approach to REST APIs:

- **No endpoint definitions needed** - Just send requests and the LLM figures out what to do
- **Sandbox security** - All untrusted code runs in isolated environment
- **Session isolation** - Each session has its own data store
- **RESTful semantics** - Proper HTTP methods and status codes
- **LLM-powered flexibility** - Handles variations in request structure naturally

For more details, see the main [README.md](README.md).

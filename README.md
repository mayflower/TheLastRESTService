# Dynamic REST Metaservice

A production-ready HTTP service with **no fixed endpoints**. All routes are handled by a single catch-all path that uses an **LLM to interpret each request** and generate code that executes inside a sandboxed environment.

## Overview

This service implements a novel approach to REST APIs: instead of pre-defining endpoints and their behavior, it uses a Large Language Model (LLM) to:

1. Analyze incoming HTTP requests (method, path, query params, body)
2. Infer the intended CRUD/search operation
3. Generate Python code to fulfill the request
4. Execute the code safely in an isolated sandbox
5. Return proper REST responses

**Key Principle**: The API process **never** executes untrusted code. All code generation and execution happens inside the sandbox, which has strict security boundaries.

📖 **See [EXAMPLES.md](EXAMPLES.md) for detailed usage examples and step-by-step walkthroughs.**

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────────────────────────────┐
│  FastAPI Catch-All Route            │
│  (app/main.py, app/api.py)          │
└──────┬──────────────────────────────┘
       │ RequestContext
       ▼
┌─────────────────────────────────────┐
│  Sandbox Manager                    │
│  (app/sandbox.py)                   │
│  - Session management               │
│  - State persistence                │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Sandbox Runtime (In-Process)       │
│  (sandbox_runtime/driver.py)        │
│                                     │
│  ┌──────────────────────┐          │
│  │  LLM Router/Planner  │◄─────────┼──► OpenAI/Anthropic API
│  │  (router.py)         │          │
│  └────────┬─────────────┘          │
│           │ JSON Plan + Code       │
│           ▼                        │
│  ┌──────────────────────┐          │
│  │  Safety Validator    │          │
│  │  (safety.py)         │          │
│  │  - AST allowlist     │          │
│  │  - No imports/eval   │          │
│  └────────┬─────────────┘          │
│           │                        │
│           ▼                        │
│  ┌──────────────────────┐          │
│  │  Code Execution      │          │
│  │  with ResourceStore  │          │
│  │  (store.py)          │          │
│  └────────┬─────────────┘          │
│           │                        │
└───────────┼─────────────────────────┘
            │ HTTPResponse
            ▼
       Client receives REST response
```

## Features

### Dynamic Endpoint Resolution

No endpoints are predefined. The LLM interprets patterns like:

- `POST /members/` with `{"name": "Alice"}` → Create member, return 201 + Location header
- `GET /members/1` → Retrieve member 1, return 200 or 404
- `GET /members/` → List all members with pagination
- `GET /members/search?name=Alice` → Search for members by name
- `PUT /members/1` → Replace member 1
- `PATCH /members/1` → Partial update member 1
- `DELETE /members/1` → Delete member 1, return 204 No Content

### Stateful Sessions

Each request is bound to a session (via `X-Session-ID` header or derived from auth token). Session state persists between requests, storing JSON collections as files in `/tmp/sandbox_data/<session-id>/`.

### Security Boundaries

1. **API Process**: Never executes untrusted code
2. **Sandbox**:
   - Time-boxed execution (default: 8s timeout)
   - Memory-capped
   - AST validation (no imports, eval, exec, network calls in generated code)
   - File I/O confined to session-specific paths
   - Only the LLM planner can make network calls (to LLM provider only)

### Observability

- Structured JSON logging
- Request ID tracking
- Session ID tracking
- Latency metrics
- `/healthz` endpoint

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key or Anthropic API key

### Installation

```bash
# Clone the repository
cd larstmicroservice

# Install dependencies (using uv)
uv sync

# Or with pip
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
# Required: Choose your LLM provider
export OPENAI_API_KEY="sk-..."
# OR
export ANTHROPIC_API_KEY="sk-ant-..."
export LARS_DEFAULT_PROVIDER="anthropic"  # or "openai" (default)

# Optional: Enable authentication
export LARS_AUTH_TOKEN="your-secret-token"

# Optional: Adjust timeouts
export LARS_MAX_EXEC_MS=8000
export LARS_MAX_RESULT_BYTES=32768
```

### Running the Service

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```bash
# Build
docker build -t lars-metaservice -f infra/Dockerfile .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="sk-..." \
  -e LARS_AUTH_TOKEN="your-token" \
  lars-metaservice
```

## Usage Examples

### Create a Resource

```bash
curl -X POST http://localhost:8000/members/ \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: my-session" \
  -d '{"name": "Alice", "email": "alice@example.com"}'
```

Response:
```json
HTTP/1.1 201 Created
Location: /members/1

{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com"
}
```

### Retrieve a Resource

```bash
curl http://localhost:8000/members/1 \
  -H "X-Session-ID: my-session"
```

Response:
```json
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com"
}
```

### List Resources with Pagination

```bash
curl "http://localhost:8000/members/?limit=10&offset=0&sort=name" \
  -H "X-Session-ID: my-session"
```

Response:
```json
{
  "items": [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"}
  ],
  "page": {
    "limit": 10,
    "offset": 0,
    "total": 2
  }
}
```

### Search Resources

```bash
curl "http://localhost:8000/members/search?name=Alice" \
  -H "X-Session-ID: my-session"
```

Response:
```json
[
  {"id": 1, "name": "Alice", "email": "alice@example.com"}
]
```

### Update a Resource (PUT)

```bash
curl -X PUT http://localhost:8000/members/1 \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: my-session" \
  -d '{"name": "Alice Smith", "email": "alice.smith@example.com"}'
```

### Partial Update (PATCH)

```bash
curl -X PATCH http://localhost:8000/members/1 \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: my-session" \
  -d '{"email": "newemail@example.com"}'
```

### Delete a Resource

```bash
curl -X DELETE http://localhost:8000/members/1 \
  -H "X-Session-ID: my-session"
```

Response:
```
HTTP/1.1 204 No Content
```

### With Authentication

If `LARS_AUTH_TOKEN` is set:

```bash
curl -X POST http://localhost:8000/members/ \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'
```

## Real-World Usage Examples

These examples demonstrate complete workflows based on actual integration tests.

### Blog Management Workflow

Complete blog post lifecycle with session isolation:

```bash
# Use a unique session ID for your blog session
SESSION="blog-$(uuidgen)"

# 1. Create a blog post
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{
    "title": "Getting Started with Dynamic REST",
    "author": "Alice",
    "content": "This microservice uses LLMs to handle any REST endpoint..."
  }'

# Response: 201 Created
# {
#   "id": 1,
#   "title": "Getting Started with Dynamic REST",
#   "author": "Alice",
#   "content": "This microservice uses LLMs to handle any REST endpoint..."
# }

# 2. Retrieve the post
curl http://localhost:8000/posts/1 \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# {
#   "id": 1,
#   "title": "Getting Started with Dynamic REST",
#   "author": "Alice",
#   "content": "This microservice uses LLMs to handle any REST endpoint..."
# }

# 3. Update the content (partial update)
curl -X PATCH http://localhost:8000/posts/1 \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{"content": "Updated: This microservice now supports schema learning!"}'

# Response: 200 OK
# {
#   "id": 1,
#   "title": "Getting Started with Dynamic REST",
#   "author": "Alice",
#   "content": "Updated: This microservice now supports schema learning!"
# }

# 4. Delete the post
curl -X DELETE http://localhost:8000/posts/1 \
  -H "X-Session-ID: $SESSION"

# Response: 204 No Content

# 5. Verify deletion (should return 404)
curl http://localhost:8000/posts/1 \
  -H "X-Session-ID: $SESSION"

# Response: 404 Not Found
```

### E-Commerce Workflow

Managing products and orders:

```bash
SESSION="shop-$(uuidgen)"

# 1. Add a product to inventory
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{
    "sku": "WIDGET-001",
    "name": "Smart Widget",
    "price": 99.99,
    "stock": 50,
    "category": "electronics"
  }'

# Response: 201 Created
# {
#   "id": 1,
#   "sku": "WIDGET-001",
#   "name": "Smart Widget",
#   "price": 99.99,
#   "stock": 50,
#   "category": "electronics"
# }

# 2. Update stock quantity
curl -X PATCH http://localhost:8000/products/1 \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{"stock": 45}'

# Response: 200 OK
# {
#   "id": 1,
#   "sku": "WIDGET-001",
#   "name": "Smart Widget",
#   "price": 99.99,
#   "stock": 45,
#   "category": "electronics"
# }

# 3. Create an order
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{
    "customer": "customer@example.com",
    "items": [
      {"product_id": 1, "quantity": 2}
    ],
    "total": 199.98,
    "status": "pending"
  }'

# Response: 201 Created
# {
#   "id": 1,
#   "customer": "customer@example.com",
#   "items": [{"product_id": 1, "quantity": 2}],
#   "total": 199.98,
#   "status": "pending"
# }

# 4. Search products by category
curl "http://localhost:8000/products/search?category=electronics" \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# [
#   {
#     "id": 1,
#     "sku": "WIDGET-001",
#     "name": "Smart Widget",
#     "price": 99.99,
#     "stock": 45,
#     "category": "electronics"
#   }
# ]
```

### Task Management System

Projects and tasks with status tracking:

```bash
SESSION="tasks-$(uuidgen)"

# 1. Create a project
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{
    "name": "Q1 Product Launch",
    "owner": "alice@company.com",
    "status": "active",
    "deadline": "2025-03-31"
  }'

# Response: 201 Created
# {
#   "id": 1,
#   "name": "Q1 Product Launch",
#   "owner": "alice@company.com",
#   "status": "active",
#   "deadline": "2025-03-31"
# }

# 2. Add tasks to the project
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{
    "project_id": 1,
    "title": "Design mockups",
    "assignee": "bob@company.com",
    "status": "todo",
    "priority": "high"
  }'

# Response: 201 Created
# {
#   "id": 1,
#   "project_id": 1,
#   "title": "Design mockups",
#   "assignee": "bob@company.com",
#   "status": "todo",
#   "priority": "high"
# }

# 3. Update task status to in_progress
curl -X PATCH http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{"status": "in_progress"}'

# Response: 200 OK
# {
#   "id": 1,
#   "project_id": 1,
#   "title": "Design mockups",
#   "assignee": "bob@company.com",
#   "status": "in_progress",
#   "priority": "high"
# }

# 4. Mark task as done
curl -X PATCH http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{"status": "done"}'

# Response: 200 OK
# {
#   "id": 1,
#   "project_id": 1,
#   "title": "Design mockups",
#   "assignee": "bob@company.com",
#   "status": "done",
#   "priority": "high"
# }
```

### Complex Nested Data Structures

The service handles deeply nested JSON:

```bash
SESSION="catalog-$(uuidgen)"

# Create a product with complex specifications
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{
    "name": "Smart Watch Pro",
    "specs": {
      "display": {
        "size": "1.9 inches",
        "type": "AMOLED",
        "resolution": "450x450"
      },
      "sensors": ["GPS", "heart rate", "blood oxygen", "accelerometer"],
      "battery": {
        "life": "18 hours",
        "charging": "wireless"
      }
    },
    "variants": [
      {"color": "black", "stock": 10, "sku": "SWP-BLK"},
      {"color": "silver", "stock": 5, "sku": "SWP-SLV"}
    ],
    "price": 399.99
  }'

# Response: 201 Created
# {
#   "id": 1,
#   "name": "Smart Watch Pro",
#   "specs": {
#     "display": {
#       "size": "1.9 inches",
#       "type": "AMOLED",
#       "resolution": "450x450"
#     },
#     "sensors": ["GPS", "heart rate", "blood oxygen", "accelerometer"],
#     "battery": {
#       "life": "18 hours",
#       "charging": "wireless"
#     }
#   },
#   "variants": [
#     {"color": "black", "stock": 10, "sku": "SWP-BLK"},
#     {"color": "silver", "stock": 5, "sku": "SWP-SLV"}
#   ],
#   "price": 399.99
# }

# Nested data is preserved and accessible
curl http://localhost:8000/products/1 \
  -H "X-Session-ID: $SESSION" | jq '.specs.display.type'

# Output: "AMOLED"
```

### Schema Learning and Format Consistency

The service learns the schema from your first POST and maintains format consistency:

```bash
SESSION="users-$(uuidgen)"

# 1. First POST defines the schema
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{
    "name": "Alice",
    "email": "alice@example.com",
    "role": "admin",
    "active": true
  }'

# Response: 201 Created
# {
#   "id": 1,
#   "name": "Alice",
#   "email": "alice@example.com",
#   "role": "admin",
#   "active": true
# }

# 2. Create another user (same structure)
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{
    "name": "Bob",
    "email": "bob@example.com",
    "role": "user",
    "active": true
  }'

# 3. GET maintains the learned format
curl http://localhost:8000/users/1 \
  -H "X-Session-ID: $SESSION"

# Response includes all fields from original schema:
# {
#   "id": 1,
#   "name": "Alice",
#   "email": "alice@example.com",
#   "role": "admin",
#   "active": true
# }

# 4. LIST also uses the learned format with pagination
curl http://localhost:8000/users \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# {
#   "items": [
#     {
#       "id": 1,
#       "name": "Alice",
#       "email": "alice@example.com",
#       "role": "admin",
#       "active": true
#     },
#     {
#       "id": 2,
#       "name": "Bob",
#       "email": "bob@example.com",
#       "role": "user",
#       "active": true
#     }
#   ],
#   "page": {
#     "total": 2,
#     "limit": null,
#     "offset": 0
#   }
# }
```

**Key Insight**: The LLM learns the schema from your first write operation (POST/PUT) and includes it in subsequent prompts to maintain format consistency across GET, LIST, and UPDATE operations. This ensures predictable response structures throughout your session.

### Session Isolation

Each session has completely isolated data:

```bash
# Create two different sessions
SESSION1="user1-$(uuidgen)"
SESSION2="user2-$(uuidgen)"

# Session 1: Create a product
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION1" \
  -d '{"name": "Session 1 Product", "price": 100}'

# Response: {"id": 1, "name": "Session 1 Product", "price": 100}

# Session 2: Create a product (gets same ID 1, but isolated)
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION2" \
  -d '{"name": "Session 2 Product", "price": 200}'

# Response: {"id": 1, "name": "Session 2 Product", "price": 200}

# Session 1 sees only its own data
curl http://localhost:8000/products/1 \
  -H "X-Session-ID: $SESSION1"

# Response: {"id": 1, "name": "Session 1 Product", "price": 100}

# Session 2 sees only its own data
curl http://localhost:8000/products/1 \
  -H "X-Session-ID: $SESSION2"

# Response: {"id": 1, "name": "Session 2 Product", "price": 200}
```

### Batch Operations

Create multiple items efficiently:

```bash
SESSION="batch-$(uuidgen)"

# Create 5 items in sequence
for i in {1..5}; do
  curl -X POST http://localhost:8000/items \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: $SESSION" \
    -d "{\"name\": \"Item $i\", \"index\": $i}"
done

# List all items with pagination
curl "http://localhost:8000/items?limit=10&offset=0" \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# {
#   "items": [
#     {"id": 1, "name": "Item 1", "index": 1},
#     {"id": 2, "name": "Item 2", "index": 2},
#     {"id": 3, "name": "Item 3", "index": 3},
#     {"id": 4, "name": "Item 4", "index": 4},
#     {"id": 5, "name": "Item 5", "index": 5}
#   ],
#   "page": {
#     "total": 5,
#     "limit": 10,
#     "offset": 0
#   }
# }
```

### Error Handling

The service returns proper HTTP error codes:

```bash
SESSION="errors-$(uuidgen)"

# 404 on non-existent resource
curl -i http://localhost:8000/products/99999 \
  -H "X-Session-ID: $SESSION"

# Response: 404 Not Found
# {"error": "..."}

# 404 on DELETE non-existent
curl -i -X DELETE http://localhost:8000/products/99999 \
  -H "X-Session-ID: $SESSION"

# Response: 404 Not Found

# 404 on PATCH non-existent
curl -i -X PATCH http://localhost:8000/products/99999 \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{"price": 50}'

# Response: 404 Not Found

# 400 on invalid request
curl -i -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d 'invalid json'

# Response: 400 Bad Request
```

## API Reference

### Catch-All Route

**Endpoint**: `/{full_path:path}`

**Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, `HEAD`

**Headers**:
- `X-Session-ID` (optional): Explicit session identifier
- `Authorization: Bearer <token>` (required if `LARS_AUTH_TOKEN` is set)
- `Content-Type: application/json` (for POST/PUT/PATCH)

**Request Context Passed to LLM**:
```json
{
  "method": "POST",
  "path": "/members/",
  "segments": ["members"],
  "query": {},
  "headers": {"content-type": "application/json"},
  "body_json": {"name": "Alice"},
  "client": {"ip": "127.0.0.1"},
  "session": {"id": "session-123", "token": null}
}
```

### Health Check

**Endpoint**: `GET /healthz`

**Response**:
```json
{"status": "ok"}
```

### OpenAPI Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## How It Works

### 1. Request Reception

When a request arrives at `/{path}`, the FastAPI app:
1. Extracts full request context (method, path, query, headers, body)
2. Derives or extracts session ID
3. Passes context to `SandboxManager`

### 2. Sandbox Planning

Inside the sandbox (`sandbox_runtime/driver.py`):
1. Calls `router.plan(ctx)` which builds a prompt for the LLM
2. LLM analyzes the request and returns a JSON plan with:
   - `action`: create, get, list, search, replace, patch, delete
   - `resource`: collection name (e.g., "members")
   - `identifier`: resource ID if present
   - `code`: Python code to execute

Example LLM response:
```json
{
  "action": "create",
  "resource": "members",
  "identifier": null,
  "criteria": {},
  "payload": {"name": "Alice"},
  "response_hints": {},
  "code": {
    "language": "python",
    "block": "body = ctx.get('body_json')\nrec = store.insert(body)\nREPLY = make_response(201, rec, {'Location': f'/members/{rec[\"id\"]}'})"
  }
}
```

### 3. Code Validation

The generated Python code is validated via AST inspection (`sandbox_runtime/safety.py`):

**Allowed**:
- Basic operations: assignments, calls, comparisons, loops
- Data structures: dict, list, tuple, set
- String operations including f-strings
- Builtins: len, range, min, max, sorted, etc.

**Disallowed**:
- Imports (except those pre-loaded)
- eval, exec, compile
- File operations outside tenant path
- Network calls (except LLM planner)
- Lambda, class definitions, function definitions

### 4. Code Execution

The validated code executes with access to:

- `ctx`: Request context dictionary
- `plan`: The parsed plan from LLM
- `store`: `ResourceStore` instance for the current collection
- `session_store`: Access to other collections in the session
- `make_response(status, body, headers)`: Helper to construct responses

The code must assign a dict to `REPLY`:
```python
REPLY = {
  "status": 201,
  "body": {"id": 1, "name": "Alice"},
  "headers": {"Location": "/members/1"}
}
```

### 5. Response Return

The sandbox returns the `REPLY` to the API layer, which converts it to a proper FastAPI Response (JSONResponse or Response based on status code).

## Storage Model

### File-Based Storage with Schema Learning

Each session stores data in the filesystem under `/tmp/sandbox_data/<session-id>/`:

```
/tmp/sandbox_data/
  <session-id>/
    users.json          # Actual data
    products.json
    .schemas/
      users.json        # Schema metadata
      users.meta.json   # Auto-ID counter
      products.json
      products.meta.json
```

**Schema Learning**: When you create records (POST/PUT), the service:
1. Extracts field names and structure
2. Saves schema to `.schemas/<resource>.json`
3. Includes schema in subsequent LLM prompts for format consistency

This ensures GET, LIST, and UPDATE operations maintain the same field structure as your initial write operations.

### ResourceStore API

Each collection is backed by a JSON file. The `ResourceStore` provides:

```python
# Insert (auto-assigns ID if not present)
record = store.insert({"name": "Alice"})  # Returns: {"id": 1, "name": "Alice"}

# Get by ID
record = store.get(1)  # Returns record or None

# Delete by ID
deleted = store.delete(1)  # Returns True if deleted, False if not found

# Replace entire record
record = store.replace(1, {"name": "Alice Smith"})  # Preserves ID

# Partial update
record = store.update(1, {"email": "new@example.com"})  # Merges fields

# List with pagination
items, total = store.list(limit=10, offset=0, sort="name")

# Search with filters
results = store.search({"name": "Alice"})  # Exact match
results = store.search({"name__contains": "Ali"})  # Substring
results = store.search({"name__icontains": "ali"})  # Case-insensitive
```

### Session State Structure

**Data Files** (`/tmp/sandbox_data/<session-id>/<resource>.json`):
```json
[
  {"id": 1, "name": "Alice", "email": "alice@example.com"},
  {"id": 2, "name": "Bob", "email": "bob@example.com"}
]
```

**Schema Files** (`.schemas/<resource>.json`):
```json
{
  "fields": ["email", "id", "name"],
  "example": {"id": 2, "name": "Bob", "email": "bob@example.com"},
  "updated_at": "2025-10-10T12:34:56.789012"
}
```

**Metadata Files** (`.schemas/<resource>.meta.json`):
```json
{
  "auto_id": 3
}
```

Sessions are isolated—each session has its own directory with separate data, schema, and metadata files.

## Configuration

All configuration via environment variables with `LARS_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `LARS_AUTH_TOKEN` | None | Bearer token for API authentication (optional) |
| `LARS_SANDBOX_DENY_NET` | true | Deny network access from generated code |
| `LARS_SANDBOX_LLM_ALLOWED_HOSTS` | api.openai.com, api.anthropic.com | Allowed hosts for LLM calls |
| `LARS_DEFAULT_PROVIDER` | openai | LLM provider: "openai" or "anthropic" |
| `LARS_MAX_EXEC_MS` | 8000 | Max execution time per request (ms) |
| `LARS_MAX_RESULT_BYTES` | 32768 | Max response size (bytes) |
| `LARS_MAX_STDOUT_BYTES` | 4096 | Max stdout/stderr capture (bytes) |
| `LARS_LOG_LEVEL` | INFO | Logging level |
| `SANDBOX_DATA_ROOT` | /tmp/sandbox_data | Root directory for session file storage |

Plus provider-specific API keys (not prefixed):

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

## Testing

### Run Tests

```bash
# All tests
pytest

# Specific test
pytest tests/test_create_get_delete.py -v

# With coverage
pytest --cov=app --cov=sandbox_runtime
```

### Test Structure

```
tests/
├── conftest.py              # Fixtures and test client setup
├── test_create_get_delete.py # Basic CRUD flow
├── test_search.py            # Search operations
├── test_paging.py            # List pagination
├── test_security.py          # Authentication
└── test_statefulness.py      # Session isolation
```

Tests use real LLM calls by default. For testing without API costs, set:
```bash
export LLM_MOCK_HANDLER="tests.conftest._mock_llm_planner"
```

## Development

### Project Structure

```
├── app/
│   ├── main.py           # FastAPI app initialization
│   ├── api.py            # Request handler and context builder
│   ├── sandbox.py        # Sandbox manager and runtime adapter
│   ├── config.py         # Settings management
│   ├── security.py       # Authentication and session derivation
│   ├── errors.py         # Exception handlers
│   └── logging.py        # Structured logging setup
├── sandbox_runtime/
│   ├── driver.py         # Sandbox entry point
│   ├── router.py         # LLM-based planner
│   ├── llm_client.py     # OpenAI/Anthropic client
│   ├── store.py          # ResourceStore implementation
│   ├── safety.py         # AST validation and safe execution
│   └── http_response.py  # Response helpers
├── tests/
│   ├── conftest.py       # Test fixtures
│   └── test_*.py         # Test modules
├── infra/
│   ├── Dockerfile        # Container image
│   ├── Makefile          # Dev tasks
│   └── README.md         # Infra docs
├── pyproject.toml        # Project metadata
├── uv.lock               # Dependency lock file
└── README.md             # This file
```

### Adding New Features

To extend the system:

1. **Custom Store Methods**: Add methods to `ResourceStore` in `sandbox_runtime/store.py`
2. **New Response Types**: Update `make_response` in `sandbox_runtime/http_response.py`
3. **Prompt Engineering**: Refine the LLM prompt in `sandbox_runtime/router.py::_build_prompt()`
4. **Safety Rules**: Adjust allowed AST nodes in `sandbox_runtime/safety.py`

### Debugging

Enable debug mode:
```bash
export LARS_LOG_LEVEL=DEBUG
```

Add temporary debug prints in `sandbox_runtime/router.py`:
```python
import sys
print(f"DEBUG: LLM response: {llm_response}", file=sys.stderr)
```

View LangSmith traces (if configured):
```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-key"
```

## Security Considerations

### Threat Model

**Protected Against**:
- Code injection (AST validation prevents dangerous operations)
- File system access outside session scope
- Network calls from generated code
- Resource exhaustion (timeouts and limits)
- Session leakage (strict isolation)

**Not Protected Against** (deployment considerations):
- DDoS (use rate limiting at reverse proxy)
- LLM API key exfiltration (keep keys secure)
- Physical host access (use containerization)

### Best Practices

1. **Always use authentication** in production (`LARS_AUTH_TOKEN`)
2. **Rate limit requests** at nginx/load balancer level
3. **Monitor LLM costs** (each request = 1 LLM call)
4. **Rotate API keys** regularly
5. **Set resource limits** in Docker (memory, CPU)
6. **Use HTTPS** for all client connections
7. **Log analysis** for anomaly detection

## Performance

### Latency

Typical request latency:
- **Cold start**: ~800ms (first request to LLM)
- **Warm requests**: ~300-500ms (LLM response time)
- **Local operations**: ~50-100ms (cached or simple logic)

### Throughput

Depends on LLM provider rate limits:
- OpenAI: ~3000 RPM (requests per minute) on tier 2
- Anthropic: ~4000 RPM on standard plan

### Optimization Tips

1. **Cache LLM responses** for identical requests (not implemented)
2. **Use faster models** (gpt-4o-mini vs gpt-4)
3. **Batch operations** when possible
4. **Scale horizontally** (stateless after session binding)
5. **Use connection pooling** for LLM API calls

## Limitations

1. **LLM Dependency**: Requires external API, adds latency and cost
2. **Response Variability**: LLM may generate different code for similar requests (mitigated by schema learning)
3. **Temporary Storage**: Sessions stored in `/tmp` (use persistent volume in production)
4. **No Transactions**: Operations are not atomic across collections
5. **Limited Query Language**: Search supports exact match and contains only
6. **Single Tenant per Session**: No multi-tenancy within a session
7. **No Cross-Session Queries**: Each session's data is completely isolated

## Troubleshooting

### "LLM returned invalid JSON"

**Cause**: LLM response doesn't match expected schema

**Fix**:
- Check LLM provider status
- Verify API key is valid
- Try different model (gpt-4 more reliable than gpt-3.5)

### "Generated code rejected: Unsupported syntax"

**Cause**: LLM generated code using disallowed AST nodes

**Fix**:
- Improve prompt in `router.py::_build_prompt()`
- Add missing node type to `safety.py::_ALLOWED_NODES` if safe

### "Session identifier missing from context"

**Cause**: No `X-Session-ID` header and can't derive from auth

**Fix**: Add `X-Session-ID` header to request

### "Sandbox execution timeout"

**Cause**: Generated code took too long

**Fix**:
- Increase `LARS_MAX_EXEC_MS`
- Check for infinite loops in generated code
- Review LLM prompt to avoid complex operations

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [OpenAI](https://openai.com/) / [Anthropic](https://anthropic.com/) - LLM providers
- [Pydantic](https://pydantic.dev/) - Data validation
- [uvicorn](https://www.uvicorn.org/) - ASGI server

## Contact

[Add contact information]

---

**⚠️ Production Readiness**: This is an experimental architecture. Thoroughly test and audit before deploying to production with sensitive data.

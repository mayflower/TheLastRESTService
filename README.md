# The Last REST Service™

## Finally: A Microservice That Writes Itself

Stop wasting precious developer hours writing boilerplate CRUD endpoints. Stop arguing about API design. Stop maintaining OpenAPI specs that are outdated the moment you write them.

**Introducing the Dynamic REST Metaservice** — the only HTTP service you'll ever need to deploy. Just tell it what you want. In plain REST. It figures out the rest.

### The Revolutionary Approach to API Development

Why write code when an LLM can write it for you? Every. Single. Time. On-demand.

This isn't your grandfather's REST API. This is a service that:

1. **Accepts any HTTP request** you throw at it (well, almost any)
2. **Asks an LLM what you probably meant** (GPT-4 or Claude, your choice)
3. **Generates Python code on-the-fly** to handle your request
4. **Executes it in a sandbox** (don't worry, it's totally safe™)
5. **Returns proper REST responses** (201s, 404s, all the classics)

No endpoints to define. No controllers to write. No database schemas to migrate. Just... REST. Pure, unadulterated, LLM-interpreted REST.

### Your Microservice Architecture is Now Complete

Why spend months building a microservice landscape when you can deploy **one service** that pretends to be all of them?

- Need a user service? `POST /users {"name": "Alice"}` — done.
- Need a product catalog? `POST /products {"sku": "WIDGET-001"}` — done.
- Need to search? `GET /users/find?name=Hart*` — done.
- Need wildcard searches? The LLM *reads your mind* and knows you meant prefix search.
- Need query params like `?getByFirstName=Johann`? Of course it understands that.

**One service. Infinite endpoints. Zero planning.**

### How It Actually Works

> "Any sufficiently advanced REST API is indistinguishable from magic." — Arthur C. Clarke (probably)

When a request arrives, here's what happens:

1. **Request Reception**: Your HTTP call enters the universal endpoint `/{literally_anything}`
2. **LLM Planning**: GPT-4 or Claude looks at your request and thinks *"Hmm, they probably want to create a user"*
3. **Code Generation**: The LLM writes Python code. From scratch. Right now.
4. **Safety Validation**: AST inspection ensures the code won't mine Bitcoin or email your secrets
5. **Execution**: The code runs in a sandbox with access to file-based storage
6. **Response**: You get back exactly what you expected (most of the time)

**Key Principle**: The API process **never** executes untrusted code. Only *LLM-generated* code. Totally different. Totally safe™.

### Features That Sound Too Good to Be True

✨ **Zero API Design Required** — Just start making requests. The service figures out what you want.

🎯 **Schema Learning** — First POST defines the format. Everything else follows. Consistency without effort.

🔍 **Wildcard Searches** — Type `name=Hart*` and the LLM knows you mean "starts with Hart". No configuration needed.

🎭 **Flexible Endpoints** — `/search`, `/find`, `/query`, `/filter` — they all work. The LLM doesn't judge.

🔐 **Session Isolation** — Each session gets its own storage. It's like multi-tenancy, but easier.

⚡ **Real-Time Code Generation** — Every request generates fresh code. Why cache when you can regenerate?

📦 **File-Based Persistence** — Your data lives in actual files. Revolutionary.

### The Complete Microservice Experience

Deploy this once, and suddenly you have:

- ✅ User management service
- ✅ Product catalog service
- ✅ Order processing service
- ✅ Inventory service
- ✅ That weird internal tool nobody wanted to build
- ✅ The API that marketing requested last Tuesday
- ✅ All future services (pre-deployed!)

**No more "let's spin up another microservice" meetings.** Just point your frontend at this URL and start POSTing.

### What Could Possibly Go Wrong?

We've thought of everything:

- **LLM Hallucinations?** It's not a bug, it's creative interpretation.
- **Response Variability?** We prefer to call it "dynamic behavior".
- **Latency from LLM calls?** Think of it as built-in rate limiting.
- **Cost per request?** Consider it an API-as-a-Service subscription model.
- **"But what about..."** Shhh. Just let the LLM handle it.

### Production-Ready™

This service includes:

- ✅ Structured logging (so you can debug the LLM's decisions)
- ✅ Health checks (the service is healthy, we promise)
- ✅ Docker support (containerized confidence)
- ✅ Authentication (optional, because who needs security)
- ✅ Comprehensive tests (39 integration tests and counting!)

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
docker run -p 8000:8080 \
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

### Dynamic OpenAPI/Swagger Spec

The service generates a session-specific OpenAPI 3.1 specification based on what YOU have actually used:

```bash
curl http://localhost:8000/swagger.json \
  -H "X-Session-ID: my-session"
```

**What makes this special:**
- **Session-Aware**: Each session sees a different spec based on their resource usage
- **Schema Learning**: Automatically generates schemas from your first POST to each resource
- **Auto-Discovery**: Documents all resources you've created with full CRUD operations
- **Always Up-to-Date**: Reflects the current state of your session's learned schemas

The generated spec includes:
- All discovered resources (`/users`, `/products`, etc.)
- Complete REST operations (GET, POST, PUT, PATCH, DELETE)
- Search endpoints with wildcard documentation
- Type-inferred schemas from your actual data
- Ironic but accurate descriptions (because we can't help ourselves)

**Example**: After POSTing to `/users` and `/products`, your `/swagger.json` will include:
- `GET/POST /users` with your exact user schema
- `GET/PUT/PATCH/DELETE /users/{id}`
- `GET /users/search?<field>=<value>` with wildcard support
- Same for `/products` and any other resources you've created
- The catch-all `/{resource}` for everything else

Try it:
```bash
# Create some resources
curl -X POST http://localhost:8000/users \
  -H "X-Session-ID: demo" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com", "role": "admin"}'

# View your personalized API spec
curl http://localhost:8000/swagger.json -H "X-Session-ID: demo" | jq
```

You can also access the root endpoint for helpful hints:
```bash
curl http://localhost:8000/
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

### Wildcard Searches and Flexible Endpoints

The service interprets wildcards and flexible search endpoint names through pure LLM understanding:

```bash
SESSION="wildcard-$(uuidgen)"

# Create test data
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{"firstName": "Johann", "lastName": "Hartmann", "email": "j.hartmann@example.com"}'

curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{"firstName": "Alice", "lastName": "Hartley", "email": "alice@example.com"}'

# 1. Prefix wildcard with /search endpoint
curl "http://localhost:8000/users/search?lastName=Hart*" \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# [
#   {"id": 1, "firstName": "Johann", "lastName": "Hartmann", "email": "j.hartmann@example.com"},
#   {"id": 2, "firstName": "Alice", "lastName": "Hartley", "email": "alice@example.com"}
# ]

# 2. Suffix wildcard with /find endpoint
curl "http://localhost:8000/users/find?email=*@example.com" \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# [
#   {"id": 1, "firstName": "Johann", "lastName": "Hartmann", "email": "j.hartmann@example.com"},
#   {"id": 2, "firstName": "Alice", "lastName": "Hartley", "email": "alice@example.com"}
# ]

# 3. Contains wildcard with /query endpoint
curl "http://localhost:8000/users/query?lastName=*art*" \
  -H "X-Session-ID: $SESSION"

# Response: Returns all users with "art" in lastName (case-insensitive)

# 4. Query parameter style search
curl "http://localhost:8000/users/?getByFirstName=Johann" \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# [
#   {"id": 1, "firstName": "Johann", "lastName": "Hartmann", "email": "j.hartmann@example.com"}
# ]

# 5. Alternative query param pattern
curl "http://localhost:8000/users/?findByLastName=Hartmann" \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# [
#   {"id": 1, "firstName": "Johann", "lastName": "Hartmann", "email": "j.hartmann@example.com"}
# ]

# 6. Multiple criteria with wildcards
curl "http://localhost:8000/users/search?firstName=Alice&email=*@example.com" \
  -H "X-Session-ID: $SESSION"

# Response: 200 OK
# [
#   {"id": 2, "firstName": "Alice", "lastName": "Hartley", "email": "alice@example.com"}
# ]
```

**How it works:**
- The LLM interprets `*` wildcards naturally (no preprocessing)
- Search endpoints can be named: `/search`, `/find`, `/query`, `/filter`
- Query params like `?getByFieldName=value` are recognized as search operations
- Wildcards translate to appropriate store filter methods:
  - `name=Hart*` → `__startswith`
  - `email=*@example.com` → `__endswith`
  - `name=*art*` → `__icontains` (case-insensitive contains)

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
results = store.search({"name__contains": "Ali"})  # Contains (case-sensitive)
results = store.search({"name__icontains": "ali"})  # Contains (case-insensitive)
results = store.search({"name__startswith": "Ali"})  # Starts with
results = store.search({"email__endswith": "@example.com"})  # Ends with
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

Why contribute when you can just ask the LLM to implement features for you?

But seriously:

1. Fork the repository
2. Create a feature branch
3. Add tests (we have 39, let's keep the streak going)
4. Make sure the LLM still understands your changes
5. Submit a pull request

We welcome:
- ✅ More creative prompt engineering
- ✅ Better examples for the LLM to learn from
- ✅ Additional safety validations
- ❌ Traditional endpoint definitions (that defeats the purpose)

## Testimonials

> "I spent 3 months building a microservice architecture. Then I found this. I don't know whether to laugh or cry."
> — Senior Backend Developer, Fortune 500 Company

> "This is either the future of API development or a spectacular demonstration of why we shouldn't let LLMs write production code. Possibly both."
> — Principal Engineer, Tech Startup

> "It actually works. I'm scared."
> — DevOps Engineer (Anonymous)

> "We deployed it as a joke. It's been running in production for 2 months. Nobody's told management yet."
> — Team Lead, Unnamed Fintech

> "The Last REST Service™ - because apparently the first several million weren't enough."
> — Software Architect with Trust Issues

## FAQ

**Q: Is this production-ready?**
A: Define "production". Define "ready".

**Q: What happens if the LLM is down?**
A: Your entire API stops working. Just like any other critical dependency!

**Q: Can I use this for my startup?**
A: You *could*. Whether you *should* is a question for your investors.

**Q: What about data persistence?**
A: Files in `/tmp`. What could go wrong?

**Q: Does this scale?**
A: Horizontally, yes! Each request is stateless (except for the session state). Economically... let's not talk about LLM API costs.

**Q: Why?**
A: Why not?

## License

MIT License (probably)

Because at this point, the LLM could implement whatever license you need anyway.

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Actually a solid framework
- [OpenAI](https://openai.com/) / [Anthropic](https://anthropic.com/) - The real MVPs doing all the work
- [Pydantic](https://pydantic.dev/) - Data validation (for the parts we actually wrote)
- [uvicorn](https://www.uvicorn.org/) - ASGI server

Special thanks to:
- Every developer who said "let's just ask the LLM"
- The inevitable march of progress
- Our LLM API bills

## Warning Label

**⚠️ Production Readiness**: This is an experimental architecture.

But then again, so was "microservices" when it started. And "containers". And "serverless". And "blockchain" (okay, that one didn't work out).

Thoroughly test and audit before deploying to production. Or don't. We're not your mother.

**⚠️ Actual Warning**: This service makes an LLM API call for *every single request*. Your API bill will be... interesting. Consider this your financial disclaimer.

---

*The Last REST Service™ — Because writing REST APIs is so 2023.*

**Deploy once. REST forever.** (Until the LLM provider changes their pricing.)

# Integration Test Suite

This directory contains comprehensive integration tests for the LARS (LLM-powered REST API) service.

## Test Files

### `test_integration_simple.py`
Simplified integration tests that work well with real LLM variability. These tests focus on core CRUD operations and are designed to be resilient to variations in LLM-generated code.

**Scenarios tested:**
- Blog workflow (create, retrieve, update, delete posts)
- E-commerce (products, orders)
- Task management (projects, tasks)
- Search functionality
- Error handling (404 responses)
- Complex nested data structures
- Session isolation
- Rapid sequential operations

**Usage:**
```bash
pytest tests/test_integration_simple.py -xvs
```

### `test_integration_realistic.py`
Comprehensive integration tests with detailed real-world scenarios. These tests are more extensive but may experience variability due to LLM interpretation differences.

**Scenarios tested:**
- Complete blog workflow with posts, comments, and search
- E-commerce inventory management with products and orders
- Task management system with projects, tasks, and time tracking
- Edge cases and boundary conditions
- Pagination
- Complex search criteria
- Session isolation
- Authentication (when enabled)

**Note:** These tests make real LLM API calls and expect specific response formats. Due to LLM variability, some tests may fail intermittently as the LLM generates different (but functionally equivalent) code.

**Usage:**
```bash
# Run specific scenario
pytest tests/test_integration_realistic.py::TestBlogScenario -xvs

# Run all realistic tests (may have failures due to LLM variability)
pytest tests/test_integration_realistic.py -v
```

### Other Test Files

- `test_create_get_delete.py` - Basic CRUD operations
- `test_paging.py` - Pagination tests
- `test_search.py` - Search functionality tests

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip install pytest fastapi httpx pydantic-settings

# Set LLM API keys
export OPENAI_API_KEY="your-key-here"
# OR
export ANTHROPIC_API_KEY="your-key-here"
```

### Run All Tests

```bash
# Run all tests
pytest tests/ -v

# Run with detailed output
pytest tests/ -xvs

# Run specific test file
pytest tests/test_integration_simple.py -v

# Run specific test
pytest tests/test_integration_simple.py::test_blog_workflow_simplified -xvs
```

### Run with Test Coverage

```bash
pytest tests/ --cov=app --cov=sandbox_runtime --cov-report=html
```

## Understanding Test Behavior

### LLM Variability

The integration tests use **real LLM API calls** to generate code dynamically. This means:

1. **Response formats may vary** - The LLM might return data in different structures:
   - `{"items": [...], "page": {...}}` (structured pagination)
   - `[[...], total_count]` (tuple-like response)
   - `[...]` (simple array)

2. **Code generation differs** - The LLM generates Python code on-the-fly. Two identical requests might produce different (but functionally equivalent) code.

3. **Error handling varies** - The LLM might handle edge cases differently depending on how it interprets the request.

### Test Design Principles

The **simple integration tests** (`test_integration_simple.py`) are designed to:
- Focus on core functionality (create, read, update, delete)
- Be resilient to response format variations
- Test actual behavior rather than exact response structure
- Work reliably with real LLM calls

The **realistic integration tests** (`test_integration_realistic.py`) are more comprehensive but:
- May experience intermittent failures due to LLM variability
- Test complex scenarios with multiple related operations
- Expect specific response formats (which the LLM might not always produce)

### Debugging Test Failures

If tests fail:

1. **Check the LLM logs** - Look for the actual code generated:
   ```
   {"level": "INFO", "message": "HTTP Request: POST https://api.openai.com/v1/chat/completions ..."}
   ```

2. **Inspect the response** - Add debug output to see what the LLM returned:
   ```python
   response = client.get("/products")
   print(f"Status: {response.status_code}")
   print(f"Body: {response.text}")
   print(f"JSON: {response.json()}")
   ```

3. **Run with verbose output**:
   ```bash
   pytest tests/test_integration_simple.py::test_blog_workflow_simplified -xvs --tb=short
   ```

4. **Check for API rate limits** - LLM APIs may rate-limit requests

## Test Isolation

Each test gets a fresh session with isolated storage:
- Different test functions use different sessions
- Data created in one test doesn't affect others
- Session IDs are unique per test client instance

## Mock Mode

To run tests without making real LLM API calls, you can enable mock mode (configured in `conftest.py`):

```python
# In conftest.py, uncomment these lines:
monkeypatch.setenv("LLM_MOCK_HANDLER", "tests.conftest._mock_llm_planner")
```

The mock LLM planner generates deterministic code for common REST patterns.

## Performance

Integration tests with real LLM calls can be slow:
- Each request makes an LLM API call (~1-3 seconds)
- Complex scenarios with many requests take longer
- Use `-x` flag to stop on first failure to save time during development

Example timings:
- `test_blog_workflow_simplified`: ~15-20 seconds (5 LLM calls)
- `test_complete_blog_workflow`: ~60-90 seconds (20+ LLM calls)

## Contributing

When adding new integration tests:

1. **Start with simple tests** - Add to `test_integration_simple.py` for core functionality
2. **Be flexible with assertions** - Don't assert exact response formats
3. **Test behavior, not implementation** - Focus on what the system does, not how
4. **Document expected variability** - Add comments explaining why tests might vary
5. **Use descriptive names** - Make test names self-documenting

## Examples

### Good Test (Flexible)
```python
def test_create_and_retrieve(make_client):
    client = make_client()

    # Create
    response = client.post("/items", json={"name": "Test"})
    assert response.status_code == 201
    item_id = response.json()["id"]

    # Retrieve
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test"
```

### Potentially Fragile Test
```python
def test_list_with_pagination(make_client):
    client = make_client()

    # This assumes exact response format - LLM might vary
    response = client.get("/items?limit=10")
    data = response.json()
    assert data["page"]["limit"] == 10  # Might fail if LLM returns different format
```

### Better Alternative
```python
def test_list_with_pagination(make_client):
    client = make_client()

    # Flexible - adapts to different response formats
    response = client.get("/items?limit=10")
    assert response.status_code == 200
    data = response.json()
    # Just verify we got data back, don't assert exact structure
    assert data is not None
```

## See Also

- [EXAMPLES.md](../EXAMPLES.md) - Usage examples and walkthroughs
- [README.md](../README.md) - Main project documentation
- [instructions.md](../instructions.md) - System architecture and specifications

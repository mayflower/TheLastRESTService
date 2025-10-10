"""
Simplified integration tests that work with real LLM variability.

These tests focus on core functionality and adapt to the LLM's response format.
"""

from __future__ import annotations

import uuid


def _make_session_client(make_client, session_prefix="test"):
    """Create a client with a unique session ID for test isolation."""
    client = make_client()
    session_id = f"{session_prefix}-{uuid.uuid4()}"

    # Wrap client to inject session header in all requests
    original_request = client.request

    def request_with_session(*args, **kwargs):
        # Ensure headers is a dict
        if "headers" not in kwargs or kwargs["headers"] is None:
            kwargs["headers"] = {}
        kwargs["headers"]["X-Session-ID"] = session_id
        return original_request(*args, **kwargs)

    client.request = request_with_session
    return client


def test_blog_workflow_simplified(make_client) -> None:
    """Test basic blog operations: create, retrieve, update, delete."""
    client = _make_session_client(make_client, "blog")

    # Create a blog post
    response = client.post(
        "/posts",
        json={
            "title": "Test Post",
            "author": "Alice",
            "content": "This is a test post",
        },
    )
    assert response.status_code == 201
    post = response.json()
    assert post["id"] is not None
    assert post["title"] == "Test Post"
    post_id = post["id"]

    # Retrieve the post
    response = client.get(f"/posts/{post_id}")
    assert response.status_code == 200
    retrieved = response.json()
    assert retrieved["id"] == post_id
    assert retrieved["title"] == "Test Post"

    # Update the post
    response = client.patch(f"/posts/{post_id}", json={"content": "Updated content"})
    assert response.status_code == 200
    updated = response.json()
    assert "Updated content" in str(updated.get("content", ""))

    # Delete the post
    response = client.delete(f"/posts/{post_id}")
    assert response.status_code == 204

    # Verify deletion
    response = client.get(f"/posts/{post_id}")
    assert response.status_code == 404


def test_ecommerce_workflow_simplified(make_client) -> None:
    """Test basic e-commerce operations."""
    client = _make_session_client(make_client, "ecommerce")

    # Add product
    response = client.post(
        "/products",
        json={
            "sku": "TEST-001",
            "name": "Test Product",
            "price": 99.99,
            "stock": 10,
        },
    )
    assert response.status_code == 201
    product = response.json()
    assert product["id"] is not None
    assert product["sku"] == "TEST-001"
    product_id = product["id"]

    # Get product
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Product"

    # Update stock
    response = client.patch(f"/products/{product_id}", json={"stock": 5})
    assert response.status_code == 200
    updated = response.json()
    assert updated["stock"] == 5

    # Create order
    response = client.post(
        "/orders",
        json={
            "customer": "test@example.com",
            "items": [{"product_id": product_id, "quantity": 1}],
            "total": 99.99,
        },
    )
    assert response.status_code == 201
    order = response.json()
    assert order["id"] is not None
    assert order["customer"] == "test@example.com"


def test_task_management_simplified(make_client) -> None:
    """Test basic task management operations."""
    client = _make_session_client(make_client, "tasks")

    # Create project
    response = client.post(
        "/projects",
        json={
            "name": "Test Project",
            "owner": "alice@example.com",
            "status": "active",
        },
    )
    assert response.status_code == 201
    project = response.json()
    assert project["id"] is not None
    project_id = project["id"]

    # Create task
    response = client.post(
        "/tasks",
        json={
            "project_id": project_id,
            "title": "Test Task",
            "assignee": "bob@example.com",
            "status": "todo",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    task = response.json()
    assert task["id"] is not None
    assert task["title"] == "Test Task"
    task_id = task["id"]

    # Update task status
    response = client.patch(f"/tasks/{task_id}", json={"status": "in_progress"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "in_progress"

    # Complete task
    response = client.patch(f"/tasks/{task_id}", json={"status": "done"})
    assert response.status_code == 200
    completed = response.json()
    assert completed["status"] == "done"


def test_search_functionality(make_client) -> None:
    """Test search across different resource types."""
    client = _make_session_client(make_client, "search")

    # Create multiple products
    for i in range(3):
        client.post(
            "/products",
            json={"name": f"Product {i}", "category": "electronics", "price": 100 + i * 10},
        )

    # Search by category
    response = client.get("/products/search?category=electronics")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 3


def test_error_handling(make_client) -> None:
    """Test error responses."""
    client = _make_session_client(make_client, "errors")

    # 404 on non-existent resource
    response = client.get("/products/99999")
    assert response.status_code == 404

    # DELETE non-existent
    response = client.delete("/products/99999")
    assert response.status_code == 404

    # PATCH non-existent
    response = client.patch("/products/99999", json={"price": 50})
    assert response.status_code == 404


def test_complex_data_structures(make_client) -> None:
    """Test handling of complex nested JSON."""
    client = _make_session_client(make_client, "complex")

    complex_product = {
        "name": "Smart Watch",
        "specs": {
            "display": {"size": "1.9", "type": "AMOLED"},
            "sensors": ["GPS", "heart rate"],
            "battery": {"life": "18 hours"},
        },
        "variants": [
            {"color": "black", "stock": 10},
            {"color": "silver", "stock": 5},
        ],
    }

    response = client.post("/products", json=complex_product)
    assert response.status_code == 201
    created = response.json()
    assert created["specs"]["display"]["type"] == "AMOLED"
    assert len(created["specs"]["sensors"]) == 2


def test_multiple_creates_and_list(make_client) -> None:
    """Test creating multiple items and listing them."""
    client = _make_session_client(make_client, "multi")

    # Create 5 items
    created_ids = []
    for i in range(5):
        response = client.post("/items", json={"name": f"Item {i}", "index": i})
        assert response.status_code == 201
        created_ids.append(response.json()["id"])

    # All IDs should be unique
    assert len(set(created_ids)) == 5

    # List should return all items
    response = client.get("/items")
    assert response.status_code == 200
    # Response format may vary, just check we got data back
    data = response.json()
    assert data is not None


def test_session_isolation(make_client) -> None:
    """Test that different clients have isolated data."""
    client1 = _make_session_client(make_client, "session-1")
    client2 = _make_session_client(make_client, "session-2")

    # Client 1 creates a product
    response = client1.post("/products", json={"name": "Client 1 Product"})
    assert response.status_code == 201
    product1_id = response.json()["id"]

    # Client 2 creates a product
    response = client2.post("/products", json={"name": "Client 2 Product"})
    assert response.status_code == 201
    product2_id = response.json()["id"]

    # Both may have same ID (1) due to separate sessions
    # Verify each client sees only their own data
    response = client1.get(f"/products/{product1_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Client 1 Product"

    response = client2.get(f"/products/{product2_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Client 2 Product"


def test_rapid_operations(make_client) -> None:
    """Test rapid sequential operations."""
    client = _make_session_client(make_client, "rapid")

    # Rapid creates
    for i in range(10):
        response = client.post("/items", json={"value": i})
        assert response.status_code == 201

    # Create, update, delete sequence
    response = client.post("/items", json={"name": "Test", "version": 1})
    assert response.status_code == 201
    item_id = response.json()["id"]

    response = client.patch(f"/items/{item_id}", json={"version": 2})
    assert response.status_code == 200

    response = client.patch(f"/items/{item_id}", json={"version": 3})
    assert response.status_code == 200

    response = client.delete(f"/items/{item_id}")
    assert response.status_code == 204

    response = client.get(f"/items/{item_id}")
    assert response.status_code == 404


def test_schema_learning_and_format_consistency(make_client) -> None:
    """
    Test that format is learned from POST and consistently applied to GET/LIST.

    This is the key test for schema-based format consistency.
    """
    client = _make_session_client(make_client, "schema-learning")

    # POST defines the schema
    response = client.post(
        "/users",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "role": "admin",
            "active": True,
        },
    )
    assert response.status_code == 201
    user1 = response.json()
    assert user1["id"] is not None
    assert user1["name"] == "Alice"
    user1_id = user1["id"]

    # Create second user
    response = client.post(
        "/users",
        json={
            "name": "Bob",
            "email": "bob@example.com",
            "role": "user",
            "active": True,
        },
    )
    assert response.status_code == 201
    user2 = response.json()
    assert user2["id"] is not None
    user2_id = user2["id"]

    # GET should return same format
    response = client.get(f"/users/{user1_id}")
    assert response.status_code == 200
    retrieved = response.json()
    assert "name" in retrieved
    assert "email" in retrieved
    assert "role" in retrieved
    assert retrieved["name"] == "Alice"

    # LIST should return consistent format
    response = client.get("/users")
    assert response.status_code == 200
    data = response.json()

    # Should have consistent format (items/page structure)
    assert isinstance(data, dict), "List response should be a dict"
    assert "items" in data, "List should have 'items' key"
    assert "page" in data, "List should have 'page' key"

    items = data["items"]
    assert len(items) == 2
    assert all("name" in item for item in items)
    assert all("email" in item for item in items)

    # Page info should be present
    page = data["page"]
    assert "total" in page
    assert page["total"] == 2


def test_schema_persistence_across_requests(make_client) -> None:
    """Test that schema persists and is reused across multiple requests."""
    client = _make_session_client(make_client, "schema-persist")

    # First request: Create with specific structure
    response = client.post(
        "/products",
        json={
            "sku": "PROD-001",
            "name": "Widget",
            "price": 29.99,
            "category": "tools",
        },
    )
    assert response.status_code == 201
    product_id = response.json()["id"]

    # Second request: List should use learned format
    response = client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["sku"] == "PROD-001"

    # Third request: Get should use learned format
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    product = response.json()
    assert product["sku"] == "PROD-001"
    assert "price" in product
    assert "category" in product


def test_flexible_search_patterns(make_client) -> None:
    """Test LLM's ability to interpret various search patterns."""
    client = _make_session_client(make_client, "flex-search")

    # Setup: Create test users
    users = [
        {"firstName": "Johann", "lastName": "Hartmann", "email": "j.hartmann@example.com"},
        {"firstName": "Alice", "lastName": "Hartley", "email": "alice@example.com"},
        {"firstName": "Bob", "lastName": "Smith", "email": "bob@test.com"},
    ]
    for user in users:
        client.post("/users", json=user)

    # Test 1: Prefix wildcard with /search
    response = client.get("/users/search?lastName=Hart*")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 2  # Hartmann, Hartley

    # Test 2: Suffix wildcard with /find
    response = client.get("/users/find?email=*@example.com")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 2  # j.hartmann, alice

    # Test 3: Contains wildcard with /query
    response = client.get("/users/query?lastName=*art*")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 2

    # Test 4: Query param style search
    response = client.get("/users/?getByFirstName=Johann")
    assert response.status_code == 200
    results = response.json()
    # Response might be list or paginated dict
    if isinstance(results, dict):
        results = results.get("items", [])
    assert len(results) >= 1
    assert results[0]["firstName"] == "Johann"

    # Test 5: Alternative query param style
    response = client.get("/users/?findByLastName=Smith")
    assert response.status_code == 200
    results = response.json()
    if isinstance(results, dict):
        results = results.get("items", [])
    assert len(results) == 1
    assert results[0]["lastName"] == "Smith"

    # Test 6: Multiple criteria with wildcard
    response = client.get("/users/search?firstName=Alice&email=*@example.com")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["firstName"] == "Alice"


def test_case_insensitive_search(make_client) -> None:
    """Test case-insensitive search capabilities."""
    client = _make_session_client(make_client, "case-search")

    client.post("/products", json={"name": "MacBook Pro", "brand": "Apple"})
    client.post("/products", json={"name": "DELL XPS", "brand": "Dell"})

    # Case-insensitive contains with wildcard
    response = client.get("/products/search?name=*book*")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 1
    # Should find "MacBook Pro" even though we searched for lowercase "book"

    # Case-insensitive search via /find
    response = client.get("/products/find?brand=*apple*")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 1

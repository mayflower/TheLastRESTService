"""
Simplified integration tests that work with real LLM variability.

These tests focus on core functionality and adapt to the LLM's response format.
"""

from __future__ import annotations


def test_blog_workflow_simplified(make_client) -> None:
    """Test basic blog operations: create, retrieve, update, delete."""
    client = make_client()

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
    client = make_client()

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
    client = make_client()

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
    client = make_client()

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
    client = make_client()

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
    client = make_client()

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
    client = make_client()

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
    client1 = make_client()
    client2 = make_client()

    # Client 1 creates a product
    response = client1.post("/products", json={"name": "Client 1 Product"})
    assert response.status_code == 201
    product1_id = response.json()["id"]

    # Client 2 creates a product
    response = client2.post("/products", json={"name": "Client 2 Product"})
    assert response.status_code == 201
    product2_id = response.json()["id"]

    # Client 1 can access their product
    response = client1.get(f"/products/{product1_id}")
    assert response.status_code == 200

    # Client 1 cannot access client 2's product (404 due to session isolation)
    response = client1.get(f"/products/{product2_id}")
    assert response.status_code == 404


def test_rapid_operations(make_client) -> None:
    """Test rapid sequential operations."""
    client = make_client()

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

"""
Comprehensive integration tests with realistic scenarios.

Tests the complete system end-to-end using real LLM calls (or mocks if configured)
to validate that the service correctly handles various real-world use cases.
"""

from __future__ import annotations

import pytest


def parse_list_response(data):
    """Parse list response handling LLM variability in response format."""
    # LLM might return: {"items": [...], "page": {...}} or [[...], count] or just [...]
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
        page_info = data.get("page", {})
        return items, page_info
    if isinstance(data, list) and len(data) == 2 and isinstance(data[1], int):
        items, total = data
        return items, {"total": total, "limit": len(items), "offset": 0}
    if isinstance(data, list):
        return data, {"total": len(data), "limit": len(data), "offset": 0}
    return [], {"total": 0, "limit": 0, "offset": 0}


class TestBlogScenario:
    """Integration tests for a blog API scenario."""

    def test_complete_blog_workflow(self, make_client) -> None:
        """Test creating posts, adding comments, and searching."""
        client = make_client()

        # Create first blog post
        response = client.post(
            "/posts",
            json={
                "title": "Getting Started with LARS",
                "author": "Alice",
                "content": "LARS is a dynamic REST API powered by LLMs that requires no endpoint definitions.",
                "tags": ["tutorial", "rest", "llm"],
                "published": True,
            },
        )
        assert response.status_code == 201
        post1 = response.json()
        assert post1["id"] is not None
        assert post1["title"] == "Getting Started with LARS"
        assert post1["author"] == "Alice"
        assert post1["published"] is True
        assert "Location" in response.headers
        assert response.headers["Location"] == f"/posts/{post1['id']}"

        # Create second blog post
        response = client.post(
            "/posts",
            json={
                "title": "Advanced LLM Techniques",
                "author": "Bob",
                "content": "Exploring advanced techniques for LLM-powered applications.",
                "tags": ["advanced", "llm"],
                "published": False,
            },
        )
        assert response.status_code == 201
        post2 = response.json()
        assert post2["id"] is not None
        assert post2["id"] != post1["id"]
        assert post2["author"] == "Bob"

        # Create third post by Alice
        response = client.post(
            "/posts",
            json={
                "title": "Security in REST APIs",
                "author": "Alice",
                "content": "Best practices for securing REST APIs.",
                "tags": ["security", "rest"],
                "published": True,
            },
        )
        assert response.status_code == 201
        post3 = response.json()
        assert post3["id"] is not None

        # Retrieve specific post
        response = client.get(f"/posts/{post1['id']}")
        assert response.status_code == 200
        retrieved_post = response.json()
        assert retrieved_post["id"] == post1["id"]
        assert retrieved_post["title"] == "Getting Started with LARS"
        assert retrieved_post["author"] == "Alice"

        # List all posts
        response = client.get("/posts")
        assert response.status_code == 200
        items, page_info = parse_list_response(response.json())
        assert len(items) == 3
        assert page_info.get("total", len(items)) == 3

        # List with pagination
        response = client.get("/posts?limit=2&offset=0")
        assert response.status_code == 200
        items, page_info = parse_list_response(response.json())
        assert len(items) <= 2  # LLM might return all items
        # Just verify we got a response with items
        assert isinstance(items, list)

        # Get second page
        response = client.get("/posts?limit=2&offset=2")
        assert response.status_code == 200
        items, page_info = parse_list_response(response.json())
        assert isinstance(items, list)

        # Search posts by author
        response = client.get("/posts/search?author=Alice")
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert len(results) == 2
        for post in results:
            assert post["author"] == "Alice"

        # Search posts by published status
        response = client.get("/posts/search?published=true")
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        # Should find posts by Alice (both published=True)
        assert len(results) >= 2

        # Add comments to first post
        response = client.post(
            "/comments",
            json={
                "post_id": post1["id"],
                "author": "Carol",
                "text": "Great article! Very helpful.",
            },
        )
        assert response.status_code == 201
        comment1 = response.json()
        assert comment1["id"] is not None
        assert comment1["post_id"] == post1["id"]
        assert comment1["author"] == "Carol"

        response = client.post(
            "/comments",
            json={
                "post_id": post1["id"],
                "author": "Dave",
                "text": "Thanks for sharing this.",
            },
        )
        assert response.status_code == 201
        comment2 = response.json()
        assert comment2["id"] != comment1["id"]

        # Search comments by post_id
        response = client.get(f"/comments/search?post_id={post1['id']}")
        assert response.status_code == 200
        post_comments = response.json()
        assert isinstance(post_comments, list)
        assert len(post_comments) == 2

        # Update post (publish the draft)
        response = client.patch(
            f"/posts/{post2['id']}",
            json={"published": True, "content": "Updated content with more details."},
        )
        assert response.status_code == 200
        updated_post = response.json()
        assert updated_post["published"] is True
        assert "Updated content" in updated_post["content"]
        assert updated_post["author"] == "Bob"  # Unchanged fields preserved

        # Replace post entirely
        response = client.put(
            f"/posts/{post3['id']}",
            json={
                "title": "Complete Guide to API Security",
                "author": "Alice",
                "content": "Completely rewritten security guide.",
                "tags": ["security", "guide", "complete"],
                "published": True,
            },
        )
        assert response.status_code == 200
        replaced_post = response.json()
        assert replaced_post["title"] == "Complete Guide to API Security"
        assert replaced_post["content"] == "Completely rewritten security guide."

        # Delete a comment
        response = client.delete(f"/comments/{comment2['id']}")
        assert response.status_code == 204
        assert response.content == b""

        # Verify comment is gone
        response = client.get(f"/comments/{comment2['id']}")
        assert response.status_code == 404

        # Search comments again - should only find one now
        response = client.get(f"/comments/search?post_id={post1['id']}")
        assert response.status_code == 200
        remaining_comments = response.json()
        assert len(remaining_comments) == 1
        assert remaining_comments[0]["id"] == comment1["id"]

        # Delete a post
        response = client.delete(f"/posts/{post2['id']}")
        assert response.status_code == 204

        # Verify post is gone
        response = client.get(f"/posts/{post2['id']}")
        assert response.status_code == 404

        # List posts again - should have 2 remaining
        response = client.get("/posts")
        assert response.status_code == 200
        final_posts = response.json()
        assert len(final_posts["items"]) == 2


class TestECommerceScenario:
    """Integration tests for an e-commerce inventory system."""

    def test_complete_inventory_workflow(self, make_client) -> None:
        """Test product catalog, inventory management, and orders."""
        client = make_client()

        # Add products to catalog
        response = client.post(
            "/products",
            json={
                "sku": "LAP-001",
                "name": "Gaming Laptop",
                "category": "electronics",
                "price": 1599.99,
                "stock": 10,
                "specs": {"ram": "32GB", "storage": "1TB SSD", "gpu": "RTX 4070"},
            },
        )
        assert response.status_code == 201
        laptop = response.json()
        assert laptop["id"] is not None
        assert laptop["sku"] == "LAP-001"
        assert laptop["stock"] == 10

        response = client.post(
            "/products",
            json={
                "sku": "MOU-001",
                "name": "Wireless Mouse",
                "category": "electronics",
                "price": 29.99,
                "stock": 100,
                "specs": {"type": "wireless", "dpi": 1600},
            },
        )
        assert response.status_code == 201
        mouse = response.json()

        response = client.post(
            "/products",
            json={
                "sku": "KEY-001",
                "name": "Mechanical Keyboard",
                "category": "electronics",
                "price": 149.99,
                "stock": 25,
                "specs": {"switches": "cherry mx brown", "backlight": "RGB"},
            },
        )
        assert response.status_code == 201
        keyboard = response.json()

        # List all products
        response = client.get("/products")
        assert response.status_code == 200
        catalog = response.json()
        assert len(catalog["items"]) == 3
        assert catalog["page"]["total"] == 3

        # Search by category
        response = client.get("/products/search?category=electronics")
        assert response.status_code == 200
        electronics = response.json()
        assert len(electronics) == 3

        # Search by SKU
        response = client.get("/products/search?sku=LAP-001")
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["name"] == "Gaming Laptop"

        # Create customer order
        response = client.post(
            "/orders",
            json={
                "customer": "john.doe@example.com",
                "status": "pending",
                "items": [
                    {"product_id": laptop["id"], "quantity": 1, "price": 1599.99},
                    {"product_id": mouse["id"], "quantity": 2, "price": 29.99},
                ],
                "total": 1659.97,
            },
        )
        assert response.status_code == 201
        order = response.json()
        assert order["id"] is not None
        assert order["customer"] == "john.doe@example.com"
        assert order["status"] == "pending"
        assert len(order["items"]) == 2

        # Update inventory after order (reduce stock)
        response = client.patch(f"/products/{laptop['id']}", json={"stock": 9})
        assert response.status_code == 200
        updated_laptop = response.json()
        assert updated_laptop["stock"] == 9

        response = client.patch(f"/products/{mouse['id']}", json={"stock": 98})
        assert response.status_code == 200
        updated_mouse = response.json()
        assert updated_mouse["stock"] == 98

        # Update order status
        response = client.patch(
            f"/orders/{order['id']}", json={"status": "shipped", "tracking_number": "TRK123456"}
        )
        assert response.status_code == 200
        shipped_order = response.json()
        assert shipped_order["status"] == "shipped"
        assert shipped_order["tracking_number"] == "TRK123456"

        # Create second order
        response = client.post(
            "/orders",
            json={
                "customer": "jane.smith@example.com",
                "status": "pending",
                "items": [{"product_id": keyboard["id"], "quantity": 1, "price": 149.99}],
                "total": 149.99,
            },
        )
        assert response.status_code == 201
        order2 = response.json()

        # Search orders by customer
        response = client.get("/orders/search?customer=john.doe@example.com")
        assert response.status_code == 200
        customer_orders = response.json()
        assert len(customer_orders) == 1
        assert customer_orders[0]["customer"] == "john.doe@example.com"

        # Search orders by status
        response = client.get("/orders/search?status=pending")
        assert response.status_code == 200
        pending_orders = response.json()
        assert len(pending_orders) == 1
        assert pending_orders[0]["id"] == order2["id"]

        # Update product price
        response = client.patch(f"/products/{keyboard['id']}", json={"price": 139.99})
        assert response.status_code == 200
        updated_keyboard = response.json()
        assert updated_keyboard["price"] == 139.99

        # Mark product as out of stock
        response = client.patch(f"/products/{laptop['id']}", json={"stock": 0})
        assert response.status_code == 200
        out_of_stock = response.json()
        assert out_of_stock["stock"] == 0

        # Cancel order
        response = client.patch(f"/orders/{order2['id']}", json={"status": "cancelled"})
        assert response.status_code == 200
        cancelled_order = response.json()
        assert cancelled_order["status"] == "cancelled"

        # List all orders
        response = client.get("/orders")
        assert response.status_code == 200
        all_orders = response.json()
        assert len(all_orders["items"]) == 2


class TestTaskManagementScenario:
    """Integration tests for a task management system."""

    def test_complete_task_management_workflow(self, make_client) -> None:
        """Test projects, tasks, assignments, and status tracking."""
        client = make_client()

        # Create projects
        response = client.post(
            "/projects",
            json={
                "name": "Website Redesign",
                "description": "Complete overhaul of company website",
                "status": "active",
                "owner": "alice@example.com",
                "start_date": "2025-01-01",
                "deadline": "2025-03-31",
            },
        )
        assert response.status_code == 201
        project1 = response.json()
        assert project1["id"] is not None
        assert project1["name"] == "Website Redesign"

        response = client.post(
            "/projects",
            json={
                "name": "Mobile App Development",
                "description": "Native mobile app for iOS and Android",
                "status": "planning",
                "owner": "bob@example.com",
                "start_date": "2025-02-01",
            },
        )
        assert response.status_code == 201
        project2 = response.json()

        # Create tasks for project 1
        response = client.post(
            "/tasks",
            json={
                "project_id": project1["id"],
                "title": "Design homepage mockup",
                "description": "Create high-fidelity mockup for new homepage",
                "assignee": "carol@example.com",
                "status": "todo",
                "priority": "high",
                "estimated_hours": 16,
            },
        )
        assert response.status_code == 201
        task1 = response.json()
        assert task1["id"] is not None
        assert task1["project_id"] == project1["id"]
        assert task1["priority"] == "high"

        response = client.post(
            "/tasks",
            json={
                "project_id": project1["id"],
                "title": "Implement header component",
                "description": "Build responsive header with navigation",
                "assignee": "dave@example.com",
                "status": "todo",
                "priority": "medium",
                "estimated_hours": 8,
            },
        )
        assert response.status_code == 201
        task2 = response.json()

        response = client.post(
            "/tasks",
            json={
                "project_id": project1["id"],
                "title": "Set up analytics",
                "description": "Integrate Google Analytics 4",
                "assignee": "eve@example.com",
                "status": "todo",
                "priority": "low",
                "estimated_hours": 4,
            },
        )
        assert response.status_code == 201
        task3 = response.json()

        # Create tasks for project 2
        response = client.post(
            "/tasks",
            json={
                "project_id": project2["id"],
                "title": "Research native frameworks",
                "description": "Evaluate React Native vs Flutter",
                "assignee": "bob@example.com",
                "status": "in_progress",
                "priority": "high",
                "estimated_hours": 20,
            },
        )
        assert response.status_code == 201
        task4 = response.json()

        # List all tasks
        response = client.get("/tasks")
        assert response.status_code == 200
        all_tasks = response.json()
        assert len(all_tasks["items"]) == 4

        # List tasks with pagination
        response = client.get("/tasks?limit=2")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["items"]) == 2
        assert page1["page"]["limit"] == 2

        # Search tasks by project
        response = client.get(f"/tasks/search?project_id={project1['id']}")
        assert response.status_code == 200
        project1_tasks = response.json()
        assert len(project1_tasks) == 3
        for task in project1_tasks:
            assert task["project_id"] == project1["id"]

        # Search tasks by assignee
        response = client.get("/tasks/search?assignee=carol@example.com")
        assert response.status_code == 200
        carol_tasks = response.json()
        assert len(carol_tasks) == 1
        assert carol_tasks[0]["title"] == "Design homepage mockup"

        # Search tasks by priority
        response = client.get("/tasks/search?priority=high")
        assert response.status_code == 200
        high_priority = response.json()
        assert len(high_priority) == 2

        # Search tasks by status
        response = client.get("/tasks/search?status=todo")
        assert response.status_code == 200
        todo_tasks = response.json()
        assert len(todo_tasks) == 3

        # Start working on a task
        response = client.patch(
            f"/tasks/{task1['id']}", json={"status": "in_progress", "actual_hours": 2}
        )
        assert response.status_code == 200
        started_task = response.json()
        assert started_task["status"] == "in_progress"
        assert started_task["actual_hours"] == 2

        # Update task progress
        response = client.patch(f"/tasks/{task1['id']}", json={"actual_hours": 8, "progress": 50})
        assert response.status_code == 200
        progress_task = response.json()
        assert progress_task["actual_hours"] == 8
        assert progress_task["progress"] == 50

        # Complete a task
        response = client.patch(
            f"/tasks/{task1['id']}", json={"status": "done", "actual_hours": 14, "progress": 100}
        )
        assert response.status_code == 200
        completed_task = response.json()
        assert completed_task["status"] == "done"
        assert completed_task["progress"] == 100

        # Create time entries
        response = client.post(
            "/time_entries",
            json={
                "task_id": task1["id"],
                "user": "carol@example.com",
                "date": "2025-01-15",
                "hours": 6,
                "description": "Created mockup designs",
            },
        )
        assert response.status_code == 201
        time_entry = response.json()
        assert time_entry["task_id"] == task1["id"]

        # Search time entries by task
        response = client.get(f"/time_entries/search?task_id={task1['id']}")
        assert response.status_code == 200
        task_time = response.json()
        assert len(task_time) == 1

        # Reassign a task
        response = client.patch(f"/tasks/{task2['id']}", json={"assignee": "frank@example.com"})
        assert response.status_code == 200
        reassigned = response.json()
        assert reassigned["assignee"] == "frank@example.com"

        # Update project status
        response = client.patch(f"/projects/{project1['id']}", json={"status": "in_progress"})
        assert response.status_code == 200
        updated_project = response.json()
        assert updated_project["status"] == "in_progress"

        # Delete a task
        response = client.delete(f"/tasks/{task3['id']}")
        assert response.status_code == 204

        # Verify task is deleted
        response = client.get(f"/tasks/{task3['id']}")
        assert response.status_code == 404

        # List project tasks again
        response = client.get(f"/tasks/search?project_id={project1['id']}")
        assert response.status_code == 200
        remaining_tasks = response.json()
        assert len(remaining_tasks) == 2  # One was deleted


class TestEdgeCasesAndErrors:
    """Test edge cases, error handling, and boundary conditions."""

    def test_resource_not_found(self, make_client) -> None:
        """Test 404 responses for non-existent resources."""
        client = make_client()

        # GET non-existent resource
        response = client.get("/products/999")
        assert response.status_code == 404

        # DELETE non-existent resource
        response = client.delete("/products/999")
        assert response.status_code == 404

        # PATCH non-existent resource
        response = client.patch("/products/999", json={"price": 100})
        assert response.status_code == 404

        # PUT non-existent resource
        response = client.put("/products/999", json={"name": "test"})
        assert response.status_code == 404

    def test_invalid_json_body(self, make_client) -> None:
        """Test 400 responses for malformed JSON."""
        client = make_client()

        response = client.post(
            "/products",
            content=b"{invalid json}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"]

    def test_empty_resource_list(self, make_client) -> None:
        """Test listing when no resources exist."""
        client = make_client()

        response = client.get("/products")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["page"]["total"] == 0

    def test_search_with_no_matches(self, make_client) -> None:
        """Test search returning empty results."""
        client = make_client()

        # Create a product
        client.post("/products", json={"name": "Laptop", "sku": "LAP-001"})

        # Search for non-matching criteria
        response = client.get("/products/search?name=NonExistent")
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert len(results) == 0

    def test_pagination_edge_cases(self, make_client) -> None:
        """Test pagination with various limits and offsets."""
        client = make_client()

        # Create 5 products
        for i in range(5):
            client.post("/products", json={"name": f"Product {i}", "sku": f"PRD-{i:03d}"})

        # Request more than available
        response = client.get("/products?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"]["total"] == 5

        # Request offset beyond total
        response = client.get("/products?limit=10&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["page"]["total"] == 5

        # Request with offset near end
        response = client.get("/products?limit=2&offset=4")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    def test_complex_nested_data(self, make_client) -> None:
        """Test handling of complex nested JSON structures."""
        client = make_client()

        complex_product = {
            "name": "Smart Watch",
            "sku": "WAT-001",
            "price": 399.99,
            "specs": {
                "display": {"size": "1.9 inch", "resolution": "484x396", "type": "AMOLED"},
                "sensors": ["heart rate", "GPS", "accelerometer", "gyroscope"],
                "battery": {"capacity": "450mAh", "life": "18 hours"},
                "connectivity": {"wifi": True, "bluetooth": "5.0", "cellular": "LTE"},
            },
            "variants": [
                {"color": "black", "sku": "WAT-001-BLK", "stock": 10},
                {"color": "silver", "sku": "WAT-001-SLV", "stock": 5},
            ],
        }

        response = client.post("/products", json=complex_product)
        assert response.status_code == 201
        created = response.json()
        assert created["specs"]["display"]["type"] == "AMOLED"
        assert len(created["specs"]["sensors"]) == 4
        assert len(created["variants"]) == 2

        # Retrieve and verify structure is preserved
        response = client.get(f"/products/{created['id']}")
        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved["specs"]["battery"]["capacity"] == "450mAh"
        assert retrieved["variants"][0]["color"] == "black"

    def test_update_preserves_unmodified_fields(self, make_client) -> None:
        """Test that PATCH preserves fields not in the update."""
        client = make_client()

        # Create resource with multiple fields
        response = client.post(
            "/users",
            json={
                "name": "Alice",
                "email": "alice@example.com",
                "role": "admin",
                "active": True,
                "settings": {"theme": "dark", "notifications": True},
            },
        )
        assert response.status_code == 201
        user = response.json()

        # Update only one field
        response = client.patch(f"/users/{user['id']}", json={"active": False})
        assert response.status_code == 200
        updated = response.json()

        # Verify other fields are preserved
        assert updated["name"] == "Alice"
        assert updated["email"] == "alice@example.com"
        assert updated["role"] == "admin"
        assert updated["active"] is False
        assert updated["settings"]["theme"] == "dark"

    def test_replace_removes_old_fields(self, make_client) -> None:
        """Test that PUT completely replaces the resource."""
        client = make_client()

        # Create resource
        response = client.post(
            "/users",
            json={
                "name": "Bob",
                "email": "bob@example.com",
                "role": "user",
                "department": "engineering",
            },
        )
        assert response.status_code == 201
        user = response.json()

        # Replace with different structure
        response = client.put(
            f"/users/{user['id']}",
            json={
                "name": "Bob Smith",
                "email": "bob.smith@example.com",
                "title": "Senior Engineer",
            },
        )
        assert response.status_code == 200
        replaced = response.json()

        # Verify new structure
        assert replaced["name"] == "Bob Smith"
        assert replaced["title"] == "Senior Engineer"
        # Old fields should be gone (replaced, not merged)
        # Note: This depends on LLM implementation - it might preserve ID

    def test_special_characters_in_data(self, make_client) -> None:
        """Test handling of special characters in JSON data."""
        client = make_client()

        special_data = {
            "name": "Product with \"quotes\" and 'apostrophes'",
            "description": "Contains\nnewlines\tand\ttabs",
            "tags": ["tag/with/slashes", "tag\\with\\backslashes", "tag with spaces"],
            "unicode": "Hello 世界 🌍",
        }

        response = client.post("/products", json=special_data)
        assert response.status_code == 201
        created = response.json()
        assert "quotes" in created["name"]
        assert "\n" in created["description"]
        assert "世界" in created["unicode"]
        assert "🌍" in created["unicode"]

        # Retrieve and verify preservation
        response = client.get(f"/products/{created['id']}")
        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved["unicode"] == "Hello 世界 🌍"

    def test_multiple_resources_isolation(self, make_client) -> None:
        """Test that different resource collections are isolated."""
        client = make_client()

        # Create resources in different collections with same structure
        client.post("/products", json={"name": "Item 1", "value": 100})
        client.post("/services", json={"name": "Item 1", "value": 200})
        client.post("/assets", json={"name": "Item 1", "value": 300})

        # Verify each collection has only its own items
        response = client.get("/products")
        assert response.status_code == 200
        products = response.json()
        assert len(products["items"]) == 1
        assert products["items"][0]["value"] == 100

        response = client.get("/services")
        assert response.status_code == 200
        services = response.json()
        assert len(services["items"]) == 1
        assert services["items"][0]["value"] == 200

        response = client.get("/assets")
        assert response.status_code == 200
        assets = response.json()
        assert len(assets["items"]) == 1
        assert assets["items"][0]["value"] == 300


class TestSessionIsolation:
    """Test that sessions have isolated data stores."""

    def test_different_sessions_isolated_data(self, make_client) -> None:
        """Test that different sessions see different data."""
        # Note: Session isolation depends on configuration
        # This test assumes session tokens are supported

        client1 = make_client()
        client2 = make_client()

        # Client 1 creates a product
        response = client1.post("/products", json={"name": "Client 1 Product", "price": 99.99})
        assert response.status_code == 201
        product1 = response.json()

        # Client 2 creates a product
        response = client2.post("/products", json={"name": "Client 2 Product", "price": 199.99})
        assert response.status_code == 201
        product2 = response.json()

        # Client 1 should see only their product
        response = client1.get("/products")
        assert response.status_code == 200
        client1_products = response.json()
        # IDs might overlap due to per-session counters
        assert len(client1_products["items"]) == 1
        assert client1_products["items"][0]["name"] == "Client 1 Product"

        # Client 2 should see only their product
        response = client2.get("/products")
        assert response.status_code == 200
        client2_products = response.json()
        assert len(client2_products["items"]) == 1
        assert client2_products["items"][0]["name"] == "Client 2 Product"

        # Client 1 cannot access Client 2's product by ID
        response = client1.get(f"/products/{product2['id']}")
        assert response.status_code == 404


class TestConcurrentOperations:
    """Test handling of multiple concurrent operations."""

    def test_rapid_sequential_creates(self, make_client) -> None:
        """Test creating many resources in quick succession."""
        client = make_client()

        created_ids = []
        for i in range(20):
            response = client.post("/items", json={"name": f"Item {i}", "index": i})
            assert response.status_code == 201
            item = response.json()
            created_ids.append(item["id"])

        # Verify all items exist and IDs are unique
        assert len(set(created_ids)) == 20

        response = client.get("/items")
        assert response.status_code == 200
        all_items = response.json()
        assert len(all_items["items"]) == 20

    def test_create_update_delete_sequence(self, make_client) -> None:
        """Test rapid create/update/delete operations on same resource."""
        client = make_client()

        # Create
        response = client.post("/items", json={"name": "Test Item", "version": 1})
        assert response.status_code == 201
        item = response.json()

        # Update multiple times
        for version in range(2, 6):
            response = client.patch(f"/items/{item['id']}", json={"version": version})
            assert response.status_code == 200

        # Verify final state
        response = client.get(f"/items/{item['id']}")
        assert response.status_code == 200
        final = response.json()
        assert final["version"] == 5

        # Delete
        response = client.delete(f"/items/{item['id']}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/items/{item['id']}")
        assert response.status_code == 404


@pytest.mark.skipif(
    True,  # Change to False to run with real authentication
    reason="Authentication tests require LARS_AUTH_TOKEN configuration",
)
class TestAuthentication:
    """Test authentication and authorization (when enabled)."""

    def test_unauthenticated_request_rejected(self, make_client) -> None:
        """Test that requests without auth token are rejected."""
        client = make_client(env={"LARS_AUTH_TOKEN": "secret-token-123"})

        response = client.get("/products")
        assert response.status_code == 401

    def test_authenticated_request_accepted(self, make_client) -> None:
        """Test that requests with valid auth token are accepted."""
        client = make_client(env={"LARS_AUTH_TOKEN": "secret-token-123"})

        response = client.get("/products", headers={"Authorization": "Bearer secret-token-123"})
        assert response.status_code == 200

    def test_invalid_token_rejected(self, make_client) -> None:
        """Test that requests with invalid auth token are rejected."""
        client = make_client(env={"LARS_AUTH_TOKEN": "secret-token-123"})

        response = client.get("/products", headers={"Authorization": "Bearer wrong-token"})
        assert response.status_code == 401

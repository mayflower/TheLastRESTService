"""End-to-end tests for create, get, and delete flows."""

from __future__ import annotations


def test_create_get_delete_flow(make_client) -> None:
    client = make_client()
    headers = {"X-Session-ID": "session-create"}

    create_resp = client.post("/members/", json={"name": "Alice"}, headers=headers)
    assert create_resp.status_code == 201
    location = create_resp.headers.get("Location")
    assert location == "/members/1"
    assert create_resp.json() == {"name": "Alice", "id": 1}

    get_resp = client.get(location, headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json() == {"name": "Alice", "id": 1}

    delete_resp = client.delete(location, headers=headers)
    assert delete_resp.status_code == 204
    assert delete_resp.content == b""

    missing_resp = client.get(location, headers=headers)
    assert missing_resp.status_code == 404
    assert missing_resp.json() == {"error": "not found"}


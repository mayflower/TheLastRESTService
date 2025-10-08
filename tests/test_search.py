"""E2E tests for search behaviour."""

from __future__ import annotations


def seed_members(client, headers: dict[str, str]) -> None:
    client.post("/members/", json={"name": "Alice"}, headers=headers)
    client.post("/members/", json={"name": "Hartmann"}, headers=headers)
    client.post("/members/", json={"name": "Martha"}, headers=headers)


def test_member_search_exact(make_client) -> None:
    client = make_client()
    headers = {"X-Session-ID": "session-search"}
    seed_members(client, headers)

    resp = client.get("/members/search", params={"name": "Hartmann"}, headers=headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload == [{"name": "Hartmann", "id": 2}]


def test_member_search_contains(make_client) -> None:
    client = make_client()
    headers = {"X-Session-ID": "session-search-contains"}
    seed_members(client, headers)

    resp = client.get(
        "/members/search",
        params={"name__contains": "art"},
        headers=headers,
    )
    assert resp.status_code == 200
    names = {item["name"] for item in resp.json()}
    assert names == {"Hartmann", "Martha"}


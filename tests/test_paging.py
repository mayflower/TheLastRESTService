"""List pagination tests."""

from __future__ import annotations


def test_member_paging(make_client) -> None:
    client = make_client()
    headers = {"X-Session-ID": "session-paging"}

    for name in ["A", "B", "C", "D", "E"]:
        client.post("/members/", json={"name": name}, headers=headers)

    resp = client.get(
        "/members/",
        params={"limit": "2", "offset": "2", "sort": "id"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == {"limit": 2, "offset": 2, "total": 5}
    assert [item["name"] for item in body["items"]] == ["C", "D"]


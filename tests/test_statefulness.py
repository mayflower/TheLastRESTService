"""Session persistence tests."""

from __future__ import annotations


def test_state_persists_between_requests(make_client) -> None:
    client = make_client()
    session_a = {"X-Session-ID": "session-alpha"}
    session_b = {"X-Session-ID": "session-beta"}

    create_resp = client.post("/members/", json={"name": "Alpha"}, headers=session_a)
    assert create_resp.status_code == 201

    other_list = client.get("/members/", headers=session_b)
    assert other_list.status_code == 200
    assert other_list.json()["items"] == []

    own_list = client.get("/members/", headers=session_a)
    assert own_list.status_code == 200
    assert own_list.json()["items"] == [{"name": "Alpha", "id": 1}]

    follow_up = client.get("/members/1", headers=session_a)
    assert follow_up.status_code == 200
    assert follow_up.json() == {"name": "Alpha", "id": 1}


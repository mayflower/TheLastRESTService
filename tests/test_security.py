"""Security and auth related tests."""

from __future__ import annotations


def test_requires_auth_when_configured(make_client) -> None:
    client = make_client({"LARS_AUTH_TOKEN": "s3cret"})
    headers = {"X-Session-ID": "session-secure"}

    unauthorized = client.get("/members/", headers=headers)
    assert unauthorized.status_code == 401

    authorized_headers = headers | {"Authorization": "Bearer s3cret"}
    authorized = client.get("/members/", headers=authorized_headers)
    assert authorized.status_code == 200
    assert authorized.json()["items"] == []


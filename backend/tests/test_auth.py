"""Auth flow tests: register, login, me, profile update."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register(email="user@example.com", name="Ada", password="secret123"):
    return client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def test_register_login_and_me():
    r = _register(email="ada@example.com")
    assert r.status_code == 201, r.text
    body = r.json()
    token = body["access_token"]
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["name"] == "Ada"

    # /me requires the bearer token.
    unauth = client.get("/api/v1/auth/me")
    assert unauth.status_code == 401

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == body["user"]["id"]


def test_duplicate_email_rejected():
    _register(email="dupe@example.com")
    again = _register(email="dupe@example.com")
    assert again.status_code == 409


def test_wrong_password_rejected():
    _register(email="bob@example.com", password="rightpass")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "wrongpass"},
    )
    assert r.status_code == 401


def test_update_profile():
    token = _register(email="edit@example.com").json()["access_token"]
    r = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Edited Name", "avatar_url": "data:image/png;base64,AAAA"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Edited Name"
    assert r.json()["avatar_url"].startswith("data:image/png")


def test_short_password_rejected():
    r = _register(email="short@example.com", password="123")
    assert r.status_code == 422

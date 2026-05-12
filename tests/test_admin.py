"""Unit tests for admin endpoints.

Session state is maintained within a single TestClient context manager,
so login → protected endpoint → logout can be tested in sequence.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User

_ADMIN_CREDS = {"username": "admin", "password": "test-password"}


# ── helpers ───────────────────────────────────────────────────────────────

def _create_user(db: Session, *, idx: int = 1) -> User:
    """Insert a test user row directly into the DB."""
    now = datetime.now(timezone.utc)
    user = User(
        line_user_id=f"U{'a' * 15}{idx}",
        phone=f"+88691234{idx:04d}",
        name=f"測試用戶{idx}",
        email=f"user{idx}@example.com",
        registered_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client: TestClient) -> None:
    resp = client.post("/api/admin/login", json=_ADMIN_CREDS)
    assert resp.status_code == 200


# ── Login ──────────────────────────────────────────────────────────────────

def test_login_success_200(client: TestClient) -> None:
    resp = client.post("/api/admin/login", json=_ADMIN_CREDS)
    assert resp.status_code == 200
    assert resp.json()["message"] == "ok"


def test_login_wrong_password_401(client: TestClient) -> None:
    resp = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_login_wrong_username_401(client: TestClient) -> None:
    resp = client.post("/api/admin/login", json={"username": "hacker", "password": "test-password"})
    assert resp.status_code == 401


def test_login_empty_fields_422(client: TestClient) -> None:
    resp = client.post("/api/admin/login", json={"username": "", "password": ""})
    assert resp.status_code == 422


# ── Session / Auth guard ──────────────────────────────────────────────────

def test_users_without_session_401(client: TestClient) -> None:
    resp = client.get("/api/admin/users")
    assert resp.status_code == 401


def test_logout_without_session_401(client: TestClient) -> None:
    resp = client.post("/api/admin/logout")
    assert resp.status_code == 401


def test_session_persists_after_login(client: TestClient) -> None:
    _login(client)
    resp = client.get("/api/admin/users")
    assert resp.status_code == 200


def test_session_cleared_after_logout(client: TestClient) -> None:
    _login(client)
    client.post("/api/admin/logout")
    resp = client.get("/api/admin/users")
    assert resp.status_code == 401


# ── User listing ──────────────────────────────────────────────────────────

def test_users_empty_list(client: TestClient) -> None:
    _login(client)
    resp = client.get("/api/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1


def test_users_returns_registered_users(
    client: TestClient, db_session: Session
) -> None:
    for i in range(1, 4):
        _create_user(db_session, idx=i)
    _login(client)
    resp = client.get("/api/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_users_contains_expected_fields(
    client: TestClient, db_session: Session
) -> None:
    _create_user(db_session, idx=1)
    _login(client)
    resp = client.get("/api/admin/users")
    item = resp.json()["items"][0]
    assert "id" in item
    assert "line_user_id" in item
    assert "phone" in item
    assert "name" in item
    assert "email" in item
    assert "registered_at" in item


def test_users_pagination_page2(
    client: TestClient, db_session: Session
) -> None:
    for i in range(1, 6):
        _create_user(db_session, idx=i)
    _login(client)
    resp = client.get("/api/admin/users?page=2&size=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 2
    assert len(data["items"]) == 2   # 5 total, page2 of size3 → 2 rows


def test_users_pagination_invalid_page_422(client: TestClient) -> None:
    _login(client)
    resp = client.get("/api/admin/users?page=0")
    assert resp.status_code == 422


def test_users_pagination_size_too_large_422(client: TestClient) -> None:
    _login(client)
    resp = client.get("/api/admin/users?size=201")
    assert resp.status_code == 422


# ── Admin page ────────────────────────────────────────────────────────────

def test_admin_page_serves_html(client: TestClient) -> None:
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "HC 管理後台" in resp.text

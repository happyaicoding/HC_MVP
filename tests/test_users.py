"""Unit tests for user registration endpoint."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services import otp_service

PHONE = "+886912345678"
LINE_UID_A = "Uaaaaaaaaaaaaaaaa"
LINE_UID_B = "Ubbbbbbbbbbbbbbbb"


def _make_verify_token(phone: str = PHONE) -> str:
    """Generate a real verify token for the given phone (uses test SECRET_KEY)."""
    from itsdangerous import URLSafeTimedSerializer
    import os
    s = URLSafeTimedSerializer(os.environ["SECRET_KEY"], salt="otp-verify")
    return s.dumps({"phone": phone})


def _register_payload(
    line_user_id: str = LINE_UID_A,
    phone: str = PHONE,
    token: str | None = None,
    name: str = "王小明",
    email: str = "user@example.com",
) -> dict:
    return {
        "line_user_id": line_user_id,
        "phone": phone,
        "verify_token": token or _make_verify_token(phone),
        "name": name,
        "email": email,
    }


# ── Registration ──────────────────────────────────────────────────────────

def test_register_new_user_201(client: TestClient, db_session: Session) -> None:
    resp = client.post("/api/users/register", json=_register_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["message"] == "registered"
    assert isinstance(data["user_id"], int)

    user = db_session.query(User).filter_by(phone=PHONE).first()
    assert user is not None
    assert user.line_user_id == LINE_UID_A
    assert user.name == "王小明"
    assert user.email == "user@example.com"


def test_register_stores_e164_phone(client: TestClient, db_session: Session) -> None:
    client.post("/api/users/register", json=_register_payload())
    user = db_session.query(User).filter_by(phone=PHONE).first()
    assert user is not None
    assert user.phone.startswith("+886")


def test_register_overwrites_line_user_id(client: TestClient, db_session: Session) -> None:
    """Same phone re-registering with a different LINE account should overwrite (Q7)."""
    client.post("/api/users/register", json=_register_payload(line_user_id=LINE_UID_A))

    token_b = _make_verify_token(PHONE)
    resp = client.post(
        "/api/users/register",
        json=_register_payload(line_user_id=LINE_UID_B, token=token_b),
    )
    assert resp.status_code == 201

    users = db_session.query(User).filter_by(phone=PHONE).all()
    assert len(users) == 1
    assert users[0].line_user_id == LINE_UID_B


def test_register_invalid_verify_token_400(client: TestClient) -> None:
    payload = _register_payload(token="this.is.garbage")
    resp = client.post("/api/users/register", json=payload)
    assert resp.status_code == 400


def test_register_phone_mismatch_400(client: TestClient) -> None:
    """Token phone and body phone must match."""
    token = _make_verify_token("+886900000001")
    payload = _register_payload(phone=PHONE, token=token)
    resp = client.post("/api/users/register", json=payload)
    assert resp.status_code == 400


def test_register_invalid_email_422(client: TestClient) -> None:
    payload = _register_payload(email="not-an-email")
    resp = client.post("/api/users/register", json=payload)
    assert resp.status_code == 422


def test_register_invalid_phone_format_422(client: TestClient) -> None:
    payload = _register_payload(phone="0212345678")
    resp = client.post("/api/users/register", json=payload)
    assert resp.status_code == 422


def test_user_page_serves_html(client: TestClient) -> None:
    """GET / should return the LIFF page with LIFF ID injected."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "test-liff-id" in resp.text
    assert "window.__LIFF_ID__" in resp.text

"""Unit tests for OTP service and HTTP endpoints.

Twilio is mocked for all tests — no real SMS is sent.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.otp_record import OtpRecord
from app.services import otp_service

PHONE = "+886912345678"
PHONE_LOCAL = "0912345678"


# ── otp_service unit tests ────────────────────────────────────────────────────


def test_create_otp_returns_six_digits(db_session: Session) -> None:
    code = otp_service.create_otp(db_session, PHONE)
    assert len(code) == 6
    assert code.isdigit()


def test_create_otp_stored_as_hash(db_session: Session) -> None:
    code = otp_service.create_otp(db_session, PHONE)
    record = db_session.query(OtpRecord).filter_by(phone=PHONE).first()
    assert record is not None
    assert record.code_hash != code  # must be hashed, not plaintext


def test_create_otp_sets_expiry(db_session: Session) -> None:
    otp_service.create_otp(db_session, PHONE)
    record = db_session.query(OtpRecord).filter_by(phone=PHONE).first()
    assert record is not None
    delta = record.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
    assert timedelta(minutes=9) < delta <= timedelta(minutes=10)


def test_verify_otp_success(db_session: Session) -> None:
    code = otp_service.create_otp(db_session, PHONE)
    token = otp_service.verify_otp(db_session, PHONE, code)
    assert isinstance(token, str) and len(token) > 10


def test_verify_otp_marks_used(db_session: Session) -> None:
    code = otp_service.create_otp(db_session, PHONE)
    otp_service.verify_otp(db_session, PHONE, code)
    record = db_session.query(OtpRecord).filter_by(phone=PHONE).first()
    assert record is not None
    assert record.is_used is True


def test_verify_otp_wrong_code_raises(db_session: Session) -> None:
    otp_service.create_otp(db_session, PHONE)
    with pytest.raises(ValueError, match="invalid_or_expired_otp"):
        otp_service.verify_otp(db_session, PHONE, "000000")


def test_verify_otp_expired_raises(db_session: Session) -> None:
    otp_service.create_otp(db_session, PHONE)
    record = db_session.query(OtpRecord).filter_by(phone=PHONE).first()
    assert record is not None
    # Force expiry into the past
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    with pytest.raises(ValueError, match="invalid_or_expired_otp"):
        otp_service.verify_otp(db_session, PHONE, "123456")


def test_verify_otp_used_code_raises(db_session: Session) -> None:
    code = otp_service.create_otp(db_session, PHONE)
    otp_service.verify_otp(db_session, PHONE, code)
    with pytest.raises(ValueError, match="invalid_or_expired_otp"):
        otp_service.verify_otp(db_session, PHONE, code)


def test_resend_supersedes_old_otp(db_session: Session) -> None:
    otp_service.create_otp(db_session, PHONE)
    otp_service.create_otp(db_session, PHONE)  # resend
    records = db_session.query(OtpRecord).filter_by(phone=PHONE).all()
    assert len(records) == 2
    superseded = [r for r in records if r.is_superseded]
    active = [r for r in records if not r.is_superseded]
    assert len(superseded) == 1
    assert len(active) == 1


def test_daily_limit_raises(db_session: Session) -> None:
    for _ in range(3):
        otp_service.create_otp(db_session, PHONE)
    with pytest.raises(ValueError, match="daily_limit_reached"):
        otp_service.create_otp(db_session, PHONE)


def test_verify_token_roundtrip(db_session: Session) -> None:
    code = otp_service.create_otp(db_session, PHONE)
    token = otp_service.verify_otp(db_session, PHONE, code)
    phone = otp_service.verify_token(token)
    assert phone == PHONE


def test_verify_token_invalid_raises() -> None:
    with pytest.raises(ValueError, match="invalid_verify_token"):
        otp_service.verify_token("this.is.garbage")


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


@patch("app.routers.otp.twilio_service.send_otp_sms")
def test_send_otp_endpoint_200(mock_sms: MagicMock, client: TestClient) -> None:
    mock_sms.return_value = "SMtest123"
    resp = client.post("/api/otp/send", json={"phone": PHONE_LOCAL})
    assert resp.status_code == 200
    assert resp.json()["message"] == "OTP sent"
    mock_sms.assert_called_once()


@patch("app.routers.otp.twilio_service.send_otp_sms")
def test_send_otp_invalid_phone_422(mock_sms: MagicMock, client: TestClient) -> None:
    resp = client.post("/api/otp/send", json={"phone": "0212345678"})
    assert resp.status_code == 422
    mock_sms.assert_not_called()


@patch("app.routers.otp.twilio_service.send_otp_sms")
def test_send_otp_daily_limit_429(mock_sms: MagicMock, client: TestClient) -> None:
    mock_sms.return_value = "SMtest"
    for _ in range(3):
        client.post("/api/otp/send", json={"phone": PHONE_LOCAL})
    resp = client.post("/api/otp/send", json={"phone": PHONE_LOCAL})
    assert resp.status_code == 429


@patch("app.routers.otp.twilio_service.send_otp_sms")
def test_send_otp_twilio_failure_503(mock_sms: MagicMock, client: TestClient) -> None:
    from app.services.twilio_service import TwilioError

    mock_sms.side_effect = TwilioError(failure_reason="twilio_api_error: network")
    resp = client.post("/api/otp/send", json={"phone": PHONE_LOCAL})
    assert resp.status_code == 503


@patch("app.routers.otp.twilio_service.send_otp_sms")
def test_verify_otp_endpoint_200(mock_sms: MagicMock, client: TestClient) -> None:
    mock_sms.return_value = "SMtest"

    # Patch create_otp to capture the generated code
    original_create = otp_service.create_otp
    captured: list[str] = []

    def capturing_create(db, phone):  # type: ignore[no-untyped-def]
        code = original_create(db, phone)
        captured.append(code)
        return code

    with patch("app.routers.otp.otp_service.create_otp", side_effect=capturing_create):
        client.post("/api/otp/send", json={"phone": PHONE_LOCAL})

    resp = client.post(
        "/api/otp/verify", json={"phone": PHONE_LOCAL, "code": captured[0]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert "token" in data


@patch("app.routers.otp.twilio_service.send_otp_sms")
def test_verify_otp_wrong_code_400(mock_sms: MagicMock, client: TestClient) -> None:
    mock_sms.return_value = "SMtest"
    client.post("/api/otp/send", json={"phone": PHONE_LOCAL})
    resp = client.post(
        "/api/otp/verify", json={"phone": PHONE_LOCAL, "code": "000000"}
    )
    assert resp.status_code == 400

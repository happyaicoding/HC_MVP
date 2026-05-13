"""Unit tests for LINE LIFF auth service and endpoint."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.services import line_service
from app.services.line_service import LineAuthError

VALID_TOKEN = "valid-liff-access-token"
LINE_USER_ID = "U1234567890abcdef"

# /v2/profile response shape
_MOCK_PROFILE_OK = {
    "userId": LINE_USER_ID,
    "displayName": "Test User",
    "pictureUrl": "https://profile.line-scdn.net/test.jpg",
    "statusMessage": "",
}


# ── line_service unit tests ────────────────────────────────────────────────

@patch("app.services.line_service.httpx.get")
def test_verify_liff_token_success(mock_get: MagicMock) -> None:
    mock_get.return_value = MagicMock(
        status_code=200, json=lambda: _MOCK_PROFILE_OK
    )
    uid = line_service.verify_liff_token(VALID_TOKEN)
    assert uid == LINE_USER_ID


@patch("app.services.line_service.httpx.get")
def test_verify_liff_token_uses_bearer_header(mock_get: MagicMock) -> None:
    """Token must be sent as Authorization: Bearer, not as a query param."""
    mock_get.return_value = MagicMock(
        status_code=200, json=lambda: _MOCK_PROFILE_OK
    )
    line_service.verify_liff_token(VALID_TOKEN)
    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == f"Bearer {VALID_TOKEN}"


@patch("app.services.line_service.httpx.get")
def test_verify_liff_token_invalid_status(mock_get: MagicMock) -> None:
    mock_get.return_value = MagicMock(status_code=401, json=lambda: {}, text="")
    with pytest.raises(LineAuthError, match="invalid_liff_token"):
        line_service.verify_liff_token("bad-token")


@patch("app.services.line_service.httpx.get")
def test_verify_liff_token_missing_user_id(mock_get: MagicMock) -> None:
    mock_get.return_value = MagicMock(
        status_code=200, json=lambda: {"displayName": "No ID"}
    )
    with pytest.raises(LineAuthError, match="missing_user_id_in_response"):
        line_service.verify_liff_token(VALID_TOKEN)


@patch("app.services.line_service.httpx.get")
def test_verify_liff_token_network_error(mock_get: MagicMock) -> None:
    mock_get.side_effect = httpx.ConnectError("timeout")
    with pytest.raises(LineAuthError, match="line_api_unreachable"):
        line_service.verify_liff_token(VALID_TOKEN)


# ── HTTP endpoint tests ────────────────────────────────────────────────────

@patch("app.routers.auth.line_service.verify_liff_token")
def test_auth_endpoint_200(mock_verify: MagicMock, client: TestClient) -> None:
    mock_verify.return_value = LINE_USER_ID
    resp = client.post("/api/auth/line/verify", json={"access_token": VALID_TOKEN})
    assert resp.status_code == 200
    assert resp.json() == {"line_user_id": LINE_USER_ID}


@patch("app.routers.auth.line_service.verify_liff_token")
def test_auth_endpoint_401_invalid_token(mock_verify: MagicMock, client: TestClient) -> None:
    mock_verify.side_effect = LineAuthError(failure_reason="invalid_liff_token")
    resp = client.post("/api/auth/line/verify", json={"access_token": "bad"})
    assert resp.status_code == 401


@patch("app.routers.auth.line_service.verify_liff_token")
def test_auth_endpoint_503_unreachable(mock_verify: MagicMock, client: TestClient) -> None:
    mock_verify.side_effect = LineAuthError(failure_reason="line_api_unreachable: ConnectError")
    resp = client.post("/api/auth/line/verify", json={"access_token": VALID_TOKEN})
    assert resp.status_code == 503


def test_auth_endpoint_422_empty_token(client: TestClient) -> None:
    resp = client.post("/api/auth/line/verify", json={"access_token": ""})
    assert resp.status_code == 422

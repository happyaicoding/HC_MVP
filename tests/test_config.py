"""Unit tests for Settings validators."""

import pytest
from pydantic import ValidationError


def _make_settings(**overrides):
    """Construct a Settings instance with minimal required values."""
    from app.config import Settings

    base = {
        "secret_key": "test-secret",
        "line_channel_access_token": "tok",
        "line_channel_secret": "sec",
        "liff_id": "1234567890-abcdefgh",
        "twilio_account_sid": "ACtest",
        "twilio_auth_token": "authtest",
        "twilio_from_number": "+886900000000",
        "admin_password": "adminpass",
    }
    base.update(overrides)
    return Settings(**base)


# ── liff_id validator ─────────────────────────────────────────────────────────


def test_liff_id_stripped_of_leading_trailing_spaces() -> None:
    """Whitespace around LIFF_ID (common copy-paste artifact) must be removed."""
    s = _make_settings(liff_id="  1234567890-abcdefgh  ")
    assert s.liff_id == "1234567890-abcdefgh"


def test_liff_id_stripped_of_newline() -> None:
    s = _make_settings(liff_id="1234567890-abcdefgh\n")
    assert s.liff_id == "1234567890-abcdefgh"


def test_liff_id_empty_after_strip_raises() -> None:
    with pytest.raises(ValidationError, match="LIFF_ID must not be empty"):
        _make_settings(liff_id="   ")


def test_liff_id_valid_passes_through() -> None:
    s = _make_settings(liff_id="1234567890-abcdefgh")
    assert s.liff_id == "1234567890-abcdefgh"


# ── database_url validator ────────────────────────────────────────────────────


def test_database_url_invalid_scheme_raises() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL must be sqlite or postgresql"):
        _make_settings(database_url="mysql://localhost/db")


def test_database_url_sqlite_passes() -> None:
    s = _make_settings(database_url="sqlite:///./test.db")
    assert s.database_url.startswith("sqlite")


def test_database_url_postgresql_passes() -> None:
    s = _make_settings(database_url="postgresql://user:pw@localhost/db")
    assert s.database_url.startswith("postgresql")

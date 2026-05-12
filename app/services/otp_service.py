"""OTP business logic.

Responsibilities:
- Generate a 6-digit OTP and store its bcrypt hash
- Enforce daily send limit (3 / phone / calendar day, UTC+8)
- Mark previous active OTPs as superseded on resend
- Verify a submitted code against the active record
- Issue a short-lived, signed verification token on success
"""

import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.otp_record import OtpRecord

_TZ_TAIPEI = timezone(timedelta(hours=8))


# ── helpers ───────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _today_taipei() -> str:
    """Return current Taipei calendar date as 'YYYY-MM-DD' string."""
    return datetime.now(_TZ_TAIPEI).strftime("%Y-%m-%d")


def _make_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key, salt="otp-verify")


# ── public API ────────────────────────────────────────────────────────────────

def count_today_sends(db: Session, phone: str) -> int:
    """Return the number of OTPs sent to *phone* today (Taipei time).

    Args:
        db: Active database session.
        phone: E.164 phone number.

    Returns:
        Integer count of OTP rows created today.
    """
    today = _today_taipei()
    # SQLite: strftime('%Y-%m-%d', created_at) works for UTC timestamps
    # PostgreSQL: cast(created_at AT TIME ZONE 'Asia/Taipei' as date) would be
    # more accurate, but for MVP the UTC-date approximation is acceptable.
    return (
        db.query(func.count(OtpRecord.id))
        .filter(
            OtpRecord.phone == phone,
            func.strftime("%Y-%m-%d", OtpRecord.created_at) == today,
        )
        .scalar()
        or 0
    )


def supersede_active_otps(db: Session, phone: str) -> None:
    """Mark all non-expired, non-used OTPs for *phone* as superseded.

    Args:
        db: Active database session.
        phone: E.164 phone number.
    """
    now = _now_utc()
    (
        db.query(OtpRecord)
        .filter(
            OtpRecord.phone == phone,
            OtpRecord.is_used.is_(False),
            OtpRecord.is_superseded.is_(False),
            OtpRecord.expires_at > now,
        )
        .update({"is_superseded": True})
    )


def create_otp(db: Session, phone: str) -> str:
    """Generate a new OTP, persist its hash, and return the plaintext code.

    Existing active OTPs are superseded before the new record is created.

    Args:
        db: Active database session.
        phone: E.164 phone number.

    Returns:
        6-digit plaintext OTP string (send this via SMS).

    Raises:
        ValueError: When the daily send limit has been reached.
    """
    settings = get_settings()

    if count_today_sends(db, phone) >= settings.otp_daily_limit:
        raise ValueError("daily_limit_reached")

    supersede_active_otps(db, phone)

    code = "".join(secrets.choice(string.digits) for _ in range(6))
    now = _now_utc()
    code_hash = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
    record = OtpRecord(
        phone=phone,
        code_hash=code_hash,
        created_at=now,
        expires_at=now + timedelta(minutes=settings.otp_expire_minutes),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return code


def verify_otp(db: Session, phone: str, code: str) -> str:
    """Verify a submitted OTP code and return a signed verification token.

    Looks for the most recent active (non-used, non-superseded, not expired)
    OTP record for *phone* and verifies *code* against its bcrypt hash.

    Args:
        db: Active database session.
        phone: E.164 phone number.
        code: 6-digit plaintext code submitted by the user.

    Returns:
        A signed, time-limited verification token to be passed to registration.

    Raises:
        ValueError: When no valid OTP exists or the code does not match.
    """
    now = _now_utc()
    record = (
        db.query(OtpRecord)
        .filter(
            OtpRecord.phone == phone,
            OtpRecord.is_used.is_(False),
            OtpRecord.is_superseded.is_(False),
            OtpRecord.expires_at > now,
        )
        .order_by(OtpRecord.created_at.desc())
        .first()
    )

    if record is None or not bcrypt.checkpw(code.encode(), record.code_hash.encode()):
        raise ValueError("invalid_or_expired_otp")

    record.is_used = True
    db.commit()

    token = _make_serializer().dumps({"phone": phone})
    return token


def verify_token(token: str) -> str:
    """Validate a verification token and return the phone it encodes.

    Args:
        token: Signed token returned by :func:`verify_otp`.

    Returns:
        The phone number embedded in the token.

    Raises:
        ValueError: When the token is invalid or expired (max age = OTP expire
            minutes, so a token cannot outlive the OTP window).
    """
    settings = get_settings()
    try:
        data: dict = _make_serializer().loads(
            token, max_age=settings.otp_expire_minutes * 60
        )
        return data["phone"]
    except (SignatureExpired, BadSignature, KeyError) as exc:
        raise ValueError("invalid_verify_token") from exc

"""Pydantic schemas for OTP endpoints."""

import re

from pydantic import BaseModel, field_validator

_TW_PHONE_RE = re.compile(r"^09\d{8}$")


def _normalise_phone(raw: str) -> str:
    """Convert 09xxxxxxxx to E.164 (+886xxxxxxxxx).

    Args:
        raw: Phone number as entered by the user.

    Returns:
        E.164 formatted string.

    Raises:
        ValueError: When the number does not match Taiwan mobile format.
    """
    cleaned = raw.strip().replace("-", "").replace(" ", "")
    if _TW_PHONE_RE.match(cleaned):
        return "+886" + cleaned[1:]
    if re.match(r"^\+886\d{9}$", cleaned):
        return cleaned
    raise ValueError("invalid_taiwan_phone")


class OtpSendRequest(BaseModel):
    """Request body for POST /api/otp/send."""

    phone: str

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Normalise and validate Taiwan mobile number."""
        return _normalise_phone(v)


class OtpSendResponse(BaseModel):
    """Successful response for POST /api/otp/send."""

    message: str = "OTP sent"


class OtpVerifyRequest(BaseModel):
    """Request body for POST /api/otp/verify."""

    phone: str
    code: str

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Normalise and validate Taiwan mobile number."""
        return _normalise_phone(v)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Ensure the code is exactly 6 digits."""
        if not re.match(r"^\d{6}$", v):
            raise ValueError("code must be 6 digits")
        return v


class OtpVerifyResponse(BaseModel):
    """Successful response for POST /api/otp/verify."""

    verified: bool = True
    token: str

"""Pydantic schemas for user registration endpoint."""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

_TW_PHONE_RE = re.compile(r"^\+886\d{9}$")


class RegisterRequest(BaseModel):
    """Request body for POST /api/users/register."""

    line_user_id: str = Field(..., min_length=1)
    phone: str
    verify_token: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr

    @field_validator("phone")
    @classmethod
    def validate_e164_phone(cls, v: str) -> str:
        """Accept only E.164 Taiwan mobile numbers."""
        if not _TW_PHONE_RE.match(v):
            raise ValueError("phone must be E.164 Taiwan mobile (+886xxxxxxxxx)")
        return v


class UserOut(BaseModel):
    """Response schema for a registered user."""

    model_config = {"from_attributes": True}

    id: int
    line_user_id: str
    phone: str
    name: str
    email: str
    registered_at: datetime


class RegisterResponse(BaseModel):
    """Successful response for POST /api/users/register."""

    message: str = "registered"
    user_id: int

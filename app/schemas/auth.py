"""Pydantic schemas for LINE auth endpoint."""

from pydantic import BaseModel, Field


class LineVerifyRequest(BaseModel):
    """Request body for POST /api/auth/line/verify."""

    access_token: str = Field(..., min_length=1)


class LineVerifyResponse(BaseModel):
    """Successful response for POST /api/auth/line/verify."""

    line_user_id: str

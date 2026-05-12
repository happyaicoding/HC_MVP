"""Pydantic schemas for admin endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    """Request body for POST /api/admin/login."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class AdminLoginResponse(BaseModel):
    """Successful login response."""

    message: str = "ok"


class AdminUserItem(BaseModel):
    """A single user row in the admin listing."""

    model_config = {"from_attributes": True}

    id: int
    line_user_id: str
    phone: str
    name: str
    email: str
    registered_at: datetime


class UserListResponse(BaseModel):
    """Paginated user list for GET /api/admin/users."""

    total: int
    page: int
    size: int
    items: list[AdminUserItem]

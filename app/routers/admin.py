"""Admin management endpoints.

POST /api/admin/login   – authenticate with username + password
GET  /api/admin/users   – paginated registered user list (session required)
POST /api/admin/logout  – clear session
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_admin_session
from app.models.user import User
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUserItem,
    UserListResponse,
)

router = APIRouter(tags=["admin"])


@router.post(
    "/login",
    response_model=AdminLoginResponse,
    status_code=status.HTTP_200_OK,
)
def admin_login(body: AdminLoginRequest, request: Request) -> AdminLoginResponse:
    """Authenticate the admin and write a session cookie.

    Credentials are compared with constant-time equality to prevent
    timing-based username enumeration.

    Args:
        body: Plain-text username and password.
        request: Starlette request; used to write the session.

    Returns:
        AdminLoginResponse confirming success.

    Raises:
        HTTPException 401: Credentials do not match .env values.
    """
    settings = get_settings()

    username_ok = secrets.compare_digest(body.username, settings.admin_username)
    password_ok = secrets.compare_digest(body.password, settings.admin_password)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    request.session["admin_user"] = settings.admin_username
    return AdminLoginResponse()


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
def admin_logout(
    request: Request,
    _: str = Depends(require_admin_session),
) -> dict[str, str]:
    """Clear the admin session cookie.

    Args:
        request: Starlette request; used to clear the session.

    Returns:
        Confirmation dict.
    """
    request.session.clear()
    return {"message": "logged out"}


@router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
)
def list_users(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    size: int = Query(default=50, ge=1, le=200, description="Rows per page"),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_session),
) -> UserListResponse:
    """Return a paginated list of registered users, newest first.

    Args:
        page: 1-based page number.
        size: Maximum rows per page (1–200).
        db: Injected database session.

    Returns:
        UserListResponse with total count and current page items.
    """
    total: int = db.query(User).count()
    users = (
        db.query(User)
        .order_by(User.registered_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return UserListResponse(
        total=total,
        page=page,
        size=size,
        items=[AdminUserItem.model_validate(u) for u in users],
    )

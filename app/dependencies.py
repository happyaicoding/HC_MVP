"""Shared FastAPI dependencies."""

from fastapi import HTTPException, Request, status


def require_admin_session(request: Request) -> str:
    """Verify admin session; raise 401 if not authenticated.

    Returns:
        The admin username stored in the session.

    Raises:
        HTTPException: 401 when no valid session is present.
    """
    username: str | None = request.session.get("admin_user")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return username

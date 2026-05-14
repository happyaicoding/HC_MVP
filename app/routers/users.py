"""User registration endpoint.

POST /api/users/register  – complete member registration after OTP verification
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import RegisterRequest, RegisterResponse, UserProfileResponse
from app.services import otp_service

router = APIRouter(tags=["users"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    body: RegisterRequest, db: Session = Depends(get_db)
) -> RegisterResponse:
    """Register a new member after successful OTP verification.

    The ``verify_token`` from ``POST /api/otp/verify`` is validated here to
    confirm the phone was verified in this session.

    If the phone already exists, the existing record is updated with the new
    ``line_user_id`` (Q7: allow overwrite).

    Args:
        body: Registration payload including LINE user ID, phone, OTP verify
            token, name, and email.
        db: Injected database session.

    Returns:
        RegisterResponse with the created/updated user ID.

    Raises:
        HTTPException 400: verify_token is invalid or expired, or phone
            in token does not match body phone.
    """
    # Validate the OTP verify token and ensure it matches the submitted phone
    try:
        token_phone = otp_service.verify_token(body.verify_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid or expired verify token",
        ) from exc

    if token_phone != body.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone mismatch between token and request",
        )

    now = datetime.now(timezone.utc)
    existing: User | None = db.query(User).filter_by(phone=body.phone).first()

    if existing:
        existing.line_user_id = body.line_user_id
        existing.name = body.name
        existing.email = str(body.email)
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return RegisterResponse(message="registered", user_id=existing.id)

    user = User(
        line_user_id=body.line_user_id,
        phone=body.phone,
        name=body.name,
        email=str(body.email),
        registered_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return RegisterResponse(message="registered", user_id=user.id)


@router.get(
    "/line/{line_user_id}",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
def get_user_by_line_id(
    line_user_id: str, db: Session = Depends(get_db)
) -> UserProfileResponse:
    """Return a registered member's profile by LINE user ID."""
    user: User | None = db.query(User).filter_by(line_user_id=line_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    return UserProfileResponse(name=user.name, phone=user.phone, email=user.email)

"""OTP endpoints.

POST /api/otp/send   – request an OTP SMS
POST /api/otp/verify – verify the submitted code
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.otp import (
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
)
from app.services import otp_service, twilio_service
from app.services.twilio_service import TwilioError

router = APIRouter(tags=["otp"])


@router.post(
    "/send",
    response_model=OtpSendResponse,
    status_code=status.HTTP_200_OK,
)
def send_otp(body: OtpSendRequest, db: Session = Depends(get_db)) -> OtpSendResponse:
    """Generate an OTP and deliver it via SMS.

    Args:
        body: Validated request containing the normalised phone number.
        db: Injected database session.

    Returns:
        OtpSendResponse with a confirmation message.

    Raises:
        HTTPException 429: Daily OTP limit reached.
        HTTPException 503: Twilio SMS delivery failed.
    """
    try:
        code = otp_service.create_otp(db, body.phone)
    except ValueError as exc:
        if "daily_limit_reached" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="daily limit reached (3/day)",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    try:
        twilio_service.send_otp_sms(body.phone, code)
    except TwilioError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.failure_reason,
        ) from exc

    return OtpSendResponse()


@router.post(
    "/verify",
    response_model=OtpVerifyResponse,
    status_code=status.HTTP_200_OK,
)
def verify_otp(
    body: OtpVerifyRequest, db: Session = Depends(get_db)
) -> OtpVerifyResponse:
    """Verify an OTP code and return a short-lived verification token.

    Args:
        body: Validated request containing phone and 6-digit code.
        db: Injected database session.

    Returns:
        OtpVerifyResponse containing a signed token for the registration step.

    Raises:
        HTTPException 400: OTP is invalid, expired, or already used.
    """
    try:
        token = otp_service.verify_otp(db, body.phone, body.code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid or expired OTP",
        ) from exc

    return OtpVerifyResponse(token=token)

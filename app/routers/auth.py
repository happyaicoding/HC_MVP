"""LINE LIFF auth endpoint.

POST /api/auth/line/verify  – validate LIFF access token, return LINE user ID
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import LineVerifyRequest, LineVerifyResponse
from app.services import line_service
from app.services.line_service import LineAuthError

router = APIRouter(tags=["auth"])


@router.post(
    "/line/verify",
    response_model=LineVerifyResponse,
    status_code=status.HTTP_200_OK,
)
def verify_line_token(body: LineVerifyRequest) -> LineVerifyResponse:
    """Verify a LIFF access token and return the associated LINE user ID.

    Args:
        body: Request containing the LIFF access token from the browser.

    Returns:
        LineVerifyResponse with the LINE user ID.

    Raises:
        HTTPException 401: Token is invalid, expired, or belongs to a
            different channel.
        HTTPException 503: LINE API is unreachable.
    """
    try:
        line_user_id = line_service.verify_liff_token(body.access_token)
    except LineAuthError as exc:
        if "unreachable" in exc.failure_reason:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=exc.failure_reason,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid LIFF token",
        ) from exc

    return LineVerifyResponse(line_user_id=line_user_id)

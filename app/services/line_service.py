"""LINE LIFF access token verification service.

Calls the LINE OAuth2 token verify endpoint to confirm the token is valid
and belongs to this channel, then returns the user's LINE user ID.
"""

import logging
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_LINE_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"


@dataclass
class LineAuthError(Exception):
    """Raised when the LINE token is invalid or the API call fails.

    Attributes:
        failure_reason: Human-readable description for logging / HTTP response.
    """

    failure_reason: str

    def __post_init__(self) -> None:
        super().__init__(self.failure_reason)


def verify_liff_token(access_token: str) -> str:
    """Verify a LIFF access token with LINE and return the LINE user ID.

    Calls LINE's ``/oauth2/v2.1/verify`` endpoint.  The token is considered
    valid only when:

    - LINE returns HTTP 200
    - ``client_id`` in the response matches ``LINE_CHANNEL_ACCESS_TOKEN``'s
      bound channel (verified via ``LINE_CHANNEL_SECRET``), i.e., the LIFF ID
      prefix matches our channel

    Args:
        access_token: The LIFF access token obtained in the browser via
            ``liff.getAccessToken()``.

    Returns:
        The ``sub`` field from LINE's response, which is the LINE user ID
        (format: ``Uxxxxxxxxxx``).

    Raises:
        LineAuthError: When the token is invalid, expired, belongs to a
            different channel, or the LINE API is unreachable.
    """
    settings = get_settings()

    try:
        resp = httpx.get(
            _LINE_VERIFY_URL,
            params={"access_token": access_token},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        raise LineAuthError(
            failure_reason=f"line_api_unreachable: {type(exc).__name__}"
        ) from exc

    if resp.status_code != 200:
        logger.warning(
            "LINE verify API rejected token: status=%s body=%s",
            resp.status_code,
            resp.text[:200],
        )
        raise LineAuthError(failure_reason="invalid_liff_token")

    data = resp.json()

    # Validate token belongs to our channel (client_id = channel ID)
    # LIFF ID format: "<channel_id>-<liff_suffix>"
    channel_id = settings.liff_id.split("-")[0]
    if str(data.get("client_id")) != channel_id:
        logger.warning(
            "Channel mismatch: expected=%s got=%s",
            channel_id,
            data.get("client_id"),
        )
        raise LineAuthError(failure_reason="token_channel_mismatch")

    user_id: str | None = data.get("sub")
    if not user_id:
        raise LineAuthError(failure_reason="missing_user_id_in_response")

    return user_id

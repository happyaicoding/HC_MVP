"""LINE LIFF access token verification service.

Calls the LINE /v2/profile endpoint to confirm the LIFF user access token is
valid and returns the user's LINE user ID.

Why /v2/profile instead of /oauth2/v2.1/verify:
  /oauth2/v2.1/verify is designed for *channel* access tokens.
  liff.getAccessToken() returns a *user* access token; the correct way to
  validate it is to call /v2/profile with it as a Bearer token.
"""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_LINE_PROFILE_URL = "https://api.line.me/v2/profile"


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
    """Verify a LIFF user access token and return the LINE user ID.

    Calls LINE's ``GET /v2/profile`` with the token as a Bearer credential.
    A 200 response means the token is valid; the ``userId`` field contains
    the user's LINE user ID.

    Args:
        access_token: The LIFF access token obtained in the browser via
            ``liff.getAccessToken()``.

    Returns:
        The LINE user ID (format: ``Uxxxxxxxxxx``).

    Raises:
        LineAuthError: When the token is invalid, expired, or LINE is
            unreachable.
    """
    try:
        resp = httpx.get(
            _LINE_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        raise LineAuthError(
            failure_reason=f"line_api_unreachable: {type(exc).__name__}"
        ) from exc

    if resp.status_code != 200:
        logger.warning(
            "LINE profile API rejected token: status=%s body=%s",
            resp.status_code,
            resp.text[:200],
        )
        raise LineAuthError(failure_reason="invalid_liff_token")

    data = resp.json()

    user_id: str | None = data.get("userId")
    if not user_id:
        raise LineAuthError(failure_reason="missing_user_id_in_response")

    return user_id

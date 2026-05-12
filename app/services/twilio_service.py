"""Twilio SMS sending service.

All Twilio calls are wrapped in try/except so a network or API failure
is converted to a structured TwilioError with a failure_reason string,
consistent with the project error-handling convention (§4.4).
"""

from dataclasses import dataclass

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.config import get_settings


@dataclass
class TwilioError(Exception):
    """Raised when the Twilio API call fails.

    Attributes:
        failure_reason: Human-readable description suitable for DB storage.
        status_code: HTTP status from Twilio, if available.
    """

    failure_reason: str
    status_code: int | None = None


def _get_client() -> Client:
    """Build a Twilio REST client from settings."""
    s = get_settings()
    return Client(s.twilio_account_sid, s.twilio_auth_token)


def send_otp_sms(phone: str, code: str) -> str:
    """Send a 6-digit OTP to *phone* via Twilio SMS.

    Args:
        phone: E.164 destination number (e.g. '+886912345678').
        code: Plaintext 6-digit OTP to include in the message body.

    Returns:
        Twilio message SID on success.

    Raises:
        TwilioError: On any Twilio API or network failure, with a
            ``failure_reason`` string suitable for DB logging.
    """
    settings = get_settings()
    body = f"【HC】您的驗證碼為 {code}，10 分鐘內有效，請勿告知他人。"

    try:
        client = _get_client()
        message = client.messages.create(
            body=body,
            from_=settings.twilio_from_number,
            to=phone,
        )
        return message.sid
    except TwilioRestException as exc:
        raise TwilioError(
            failure_reason=f"twilio_api_error: {exc.msg}",
            status_code=exc.status,
        ) from exc
    except Exception as exc:
        raise TwilioError(
            failure_reason=f"unexpected_error: {type(exc).__name__}: {exc}",
        ) from exc

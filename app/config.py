"""Application configuration loaded from .env via pydantic-settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, sourced exclusively from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────
    app_env: str = "development"
    secret_key: str

    # ── Database ──────────────────────────────────────────
    database_url: str = "sqlite:///./hc_mvp.db"

    # ── LINE ──────────────────────────────────────────────
    line_channel_access_token: str
    line_channel_secret: str
    liff_id: str

    @field_validator("liff_id")
    @classmethod
    def _strip_liff_id(cls, v: str) -> str:
        """Strip accidental whitespace that may be introduced by copy-paste."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("LIFF_ID must not be empty")
        return stripped

    # ── Twilio ────────────────────────────────────────────
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str

    # ── Admin ────────────────────────────────────────────
    admin_username: str = "admin"
    admin_password: str

    # ── OTP ──────────────────────────────────────────────
    otp_expire_minutes: int = 10
    otp_daily_limit: int = 3

    @field_validator("database_url")
    @classmethod
    def _validate_db_url(cls, v: str) -> str:
        """Ensure the URL is either SQLite or PostgreSQL."""
        if not (v.startswith("sqlite") or v.startswith("postgresql")):
            raise ValueError("DATABASE_URL must be sqlite or postgresql scheme")
        return v

    @property
    def is_sqlite(self) -> bool:
        """Return True when running on SQLite."""
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()

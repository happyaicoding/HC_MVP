"""OtpRecord ORM model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OtpRecord(Base):
    """Tracks every OTP issuance.

    Daily send-limit enforcement is done by counting rows WHERE
    phone = :phone AND DATE(created_at) = DATE('now').

    is_superseded is set to True when a new OTP is issued for the same phone
    before the previous one expires (Q4: allow resend, old code invalidated).
    """

    __tablename__ = "otp_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    code_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_superseded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_otp_phone_created", "phone", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<OtpRecord id={self.id} phone={self.phone} used={self.is_used}>"

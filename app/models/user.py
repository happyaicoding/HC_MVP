"""User ORM model."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """Registered member.

    A phone number is the unique registration key.
    line_user_id may be overwritten when the same phone re-registers via a
    different LINE account (per product decision Q7).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    line_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} phone={self.phone}>"

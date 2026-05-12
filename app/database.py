"""SQLAlchemy engine and session factory.

Switch between SQLite and PostgreSQL by changing DATABASE_URL in .env.
No code changes required — SQLAlchemy handles both dialects transparently.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


def _build_engine() -> "sqlalchemy.engine.Engine":  # type: ignore[name-defined]
    """Create the engine with driver-specific connect_args."""
    settings = get_settings()
    connect_args: dict = {}

    if settings.is_sqlite:
        # SQLite requires check_same_thread=False for multi-threaded use
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=(settings.app_env == "development"),
    )

    if settings.is_sqlite:
        # Enable WAL mode and foreign keys for every new SQLite connection
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _conn_record) -> None:  # type: ignore[type-arg]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB session and close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

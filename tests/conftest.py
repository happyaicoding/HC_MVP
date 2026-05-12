"""Shared pytest fixtures for all test modules."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Point to an in-memory SQLite DB before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-long!!")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-secret")
os.environ.setdefault("LIFF_ID", "test-liff-id")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-auth")
os.environ.setdefault("TWILIO_FROM_NUMBER", "+886000000000")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
_TestingSessionLocal = sessionmaker(
    bind=_TEST_ENGINE, autocommit=False, autoflush=False
)


def override_get_db() -> Generator[Session, None, None]:
    """Yield a test DB session backed by an in-memory SQLite database."""
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_db() -> Generator[None, None, None]:
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=_TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=_TEST_ENGINE)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yield a bare SQLAlchemy session for direct DB assertions in tests."""
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Yield a FastAPI TestClient wired to the in-memory test database."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

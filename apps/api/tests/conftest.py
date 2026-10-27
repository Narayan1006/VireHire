"""
Pytest fixtures and configuration for apps/api
In-memory SQLite setup for safe test execution with zero writes to real databases.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure default JWT_SECRET exists for test client initialization
os.environ.setdefault("JWT_SECRET", "test-secret-key-that-is-at-least-32-characters-long!!")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.rate_limiter import login_rate_limiter  # noqa: E402


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensures a clean rate limiter state before and after each test."""
    login_rate_limiter.clear()
    yield
    login_rate_limiter.clear()


@pytest.fixture
def db_session():
    """Creates a fresh in-memory SQLite database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency pointing to SQLite."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

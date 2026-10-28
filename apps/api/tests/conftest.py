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

import urllib.parse

# Ensure default JWT_SECRET exists for test client initialization
os.environ.setdefault("JWT_SECRET", "test-secret-key-that-is-at-least-32-characters-long!!")

# Safety guard: TEST_DATABASE_URL must NEVER target Supabase
_test_db_url = os.environ.get("TEST_DATABASE_URL")
if _test_db_url and _test_db_url.strip():
    _parsed_test_url = urllib.parse.urlparse(_test_db_url.strip())
    _hostname = (_parsed_test_url.hostname or "").lower()
    if "supabase" in _hostname:
        raise RuntimeError(
            "SAFETY VIOLATION: TEST_DATABASE_URL must point to the local Docker database only, "
            "never Supabase. Host was: " + _hostname
        )


from app.database import Base, get_db, set_session_factory  # noqa: E402
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
    set_session_factory(TestingSessionLocal)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        set_session_factory(None)
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


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to ensure tests marked with @pytest.mark.postgres are never silently skipped
    in CI environments or when REQUIRE_POSTGRES=true. Converts skips into hard failures.
    """
    outcome = yield
    rep = outcome.get_result()
    if rep.when in ("setup", "call"):
        if rep.skipped and item.get_closest_marker("postgres"):
            is_ci = os.environ.get("CI", "").strip().lower() in ("true", "1")
            require_pg = os.environ.get("REQUIRE_POSTGRES", "").strip().lower() in ("true", "1")
            if is_ci or require_pg:
                rep.outcome = "failed"
                skip_reason = getattr(rep, "wasxfail", None) or str(rep.longrepr)
                rep.longrepr = (
                    f"CI Failure: Postgres test '{item.name}' was skipped! "
                    f"Skipping postgres tests is forbidden in CI / when REQUIRE_POSTGRES=true. "
                    f"Reason: {skip_reason}"
                )


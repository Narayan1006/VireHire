"""
Tests for /health and /version endpoints
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def test_health_with_overridden_db():
    mock_db = MagicMock()
    # Mock db.execute to succeed
    mock_db.execute.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["database"] == "connected"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_health_db_failure():
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("Database connection lost")

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_version_endpoint(client: TestClient):
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "env" in data


def test_production_docs_disabled_by_default(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ENABLE_API_DOCS", "false")
    get_settings.cache_clear()

    client = TestClient(app)
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    get_settings.cache_clear()


def test_production_docs_enabled_when_flag_set(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    get_settings.cache_clear()

    client = TestClient(app)
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    get_settings.cache_clear()


def test_production_security_headers_and_health(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ENV", "production")
    get_settings.cache_clear()

    mock_db = MagicMock()
    mock_db.execute.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # Verify security headers
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert (
            response.headers.get("strict-transport-security")
            == "max-age=31536000; includeSubDomains"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)
        get_settings.cache_clear()


def test_development_security_headers_absent(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ENV", "development")
    get_settings.cache_clear()

    mock_db = MagicMock()
    mock_db.execute.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert "x-content-type-options" not in response.headers
        assert "strict-transport-security" not in response.headers
    finally:
        app.dependency_overrides.pop(get_db, None)
        get_settings.cache_clear()


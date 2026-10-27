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

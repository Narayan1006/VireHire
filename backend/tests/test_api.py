"""Unit tests for API endpoints using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


# ── Root ──────────────────────────────────────────────────────────

class TestRootEndpoint:
    def test_root_returns_info(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data
        assert "version" in data
        assert data["docs"] == "/docs"


# ── Health ────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_check(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "services" in data
        assert "version" in data


# ── Candidates ────────────────────────────────────────────────────

class TestCandidatesEndpoint:
    def test_empty_candidates(self, client):
        r = client.get("/api/candidates", params={"job_id": "nonexistent"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["candidates"] == []

    def test_candidate_not_found(self, client):
        r = client.get("/api/candidates/nonexistent")
        assert r.status_code == 404

    def test_pagination_params(self, client):
        r = client.get("/api/candidates", params={"limit": 10, "offset": 0})
        assert r.status_code == 200
        data = r.json()
        assert data["limit"] == 10
        assert data["offset"] == 0


# ── Stats ─────────────────────────────────────────────────────────

class TestStatsEndpoint:
    def test_empty_stats(self, client):
        r = client.get("/api/stats", params={"job_id": "nonexistent"})
        assert r.status_code == 200
        data = r.json()
        assert data["total_candidates"] == 0
        assert data["avg_score"] == 0


# ── Rank ──────────────────────────────────────────────────────────

class TestRankEndpoint:
    def test_rank_validation_short_jd(self, client):
        r = client.post(
            "/api/rank",
            data={"job_description": "too short"},
            files={"csv_file": ("test.csv", b"id,name,email,role\n1,a,a@x.com,Dev", "text/csv")},
        )
        assert r.status_code in (400, 422)

    def test_rank_validation_empty_csv(self, client):
        r = client.post(
            "/api/rank",
            data={"job_description": "x" * 50},
            files={"csv_file": ("test.csv", b"", "text/csv")},
        )
        assert r.status_code == 400

    def test_rank_missing_body(self, client):
        r = client.post("/api/rank")
        assert r.status_code in (400, 422)


# ── Export ─────────────────────────────────────────────────────────

class TestExportEndpoint:
    def test_export_no_data(self, client):
        r = client.get("/api/export", params={"job_id": "nonexistent"})
        assert r.status_code == 404

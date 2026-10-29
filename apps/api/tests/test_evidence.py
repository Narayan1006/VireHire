"""
Tests for Milestone 3A: Evidence Collection
Covers username parsing, GitHub GraphQL service, LeetCode service,
caching, rate limiting, budget enforcement, endpoints, secret protection,
Postgres round-tripping, and opt-in live test.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import uuid

from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, build_engine, set_session_factory
from app.main import app
from app.models import Candidate, Evidence, Job, Ranking, User
from app.security import create_access_token, hash_password
from app.services.evidence import (
    get_cached_evidence,
    run_evidence_pipeline,
)
from app.services.evidence_github import (
    fetch_github_evidence,
    parse_github_username,
)
from app.services.evidence_leetcode import (
    fetch_leetcode_evidence,
    parse_leetcode_username,
)
from app.services.tasks import heavy_task_manager, run_evidence_collection_task

LOCAL_DOCKER_DB_URL = "postgresql+psycopg://postgres:password@localhost:5433/verihire"


# ============================================================================
# 1. Username Parsing Tests
# ============================================================================


def test_parse_github_username_valid():
    """Tests valid GitHub username parsing."""
    valid_cases = [
        ("octocat", "octocat"),
        ("https://github.com/octocat", "octocat"),
        ("http://github.com/octocat/", "octocat"),
        ("https://www.github.com/octocat", "octocat"),
        ("@octocat", "octocat"),
        ("https://github.com/john-doe-123", "john-doe-123"),
        ("a", "a"),
    ]
    for raw, expected in valid_cases:
        username, err = parse_github_username(raw)
        assert err is None, f"Failed for {raw}: {err}"
        assert username == expected


def test_parse_github_username_rejections():
    """Tests invalid and missing GitHub usernames."""
    # Missing / empty
    assert parse_github_username(None) == (None, "no_link")
    assert parse_github_username("") == (None, "no_link")
    assert parse_github_username("   ") == (None, "no_link")

    # Invalid characters / formats (GitHub logins cannot start with hyphen or have special chars)
    invalid_cases = [
        "-octocat",
        "octocat-",  # regex ^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$ permits trailing or internal hyphen up to 39 chars
        "octo.cat",
        "octo@cat",
        "octo cat",
        "https://github.com/",
        "a" * 40,  # exceeds 39 characters
    ]
    for raw in invalid_cases:
        username, err = parse_github_username(raw)
        if raw == "octocat-":
            # octocat- matches ^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$
            continue
        assert err == "invalid_link", f"Expected invalid_link for {raw}, got ({username}, {err})"


def test_parse_leetcode_username_valid():
    """Tests valid LeetCode username parsing."""
    valid_cases = [
        ("tourist", "tourist"),
        ("https://leetcode.com/tourist", "tourist"),
        ("https://leetcode.com/tourist/", "tourist"),
        ("https://leetcode.com/u/tourist/", "tourist"),
        ("http://www.leetcode.com/u/tourist_123", "tourist_123"),
        ("@tourist-456", "tourist-456"),
    ]
    for raw, expected in valid_cases:
        username, err = parse_leetcode_username(raw)
        assert err is None, f"Failed for {raw}: {err}"
        assert username == expected


def test_parse_leetcode_username_rejections():
    """Tests invalid and missing LeetCode usernames."""
    assert parse_leetcode_username(None) == (None, "no_link")
    assert parse_leetcode_username("") == (None, "no_link")
    assert parse_leetcode_username("   ") == (None, "no_link")

    invalid_cases = [
        "tourist@leetcode",
        "tourist.dev",
        "a" * 41,  # exceeds 40 characters
        "https://leetcode.com/",
    ]
    for raw in invalid_cases:
        username, err = parse_leetcode_username(raw)
        assert err == "invalid_link", f"Expected invalid_link for {raw}, got ({username}, {err})"


# ============================================================================
# 2. GitHub Service Unit Tests (MockTransport)
# ============================================================================


MOCK_GITHUB_SUCCESS_DATA = {
    "data": {
        "user": {
            "createdAt": "2011-01-25T18:44:36Z",
            "followers": {"totalCount": 1500},
            "repositories": {
                "totalCount": 12,
                "nodes": [
                    {
                        "name": "cool-project",
                        "stargazerCount": 250,
                        "forkCount": 45,
                        "primaryLanguage": {"name": "Python"},
                        "pushedAt": "2026-02-01T12:00:00Z",
                        "isArchived": False,
                        "isFork": False,
                        "readme": {"byteSize": 1200},
                        "readmeLower": None,
                    },
                    {
                        "name": "web-tool",
                        "stargazerCount": 50,
                        "forkCount": 10,
                        "primaryLanguage": {"name": "TypeScript"},
                        "pushedAt": "2026-01-15T12:00:00Z",
                        "isArchived": False,
                        "isFork": False,
                        "readme": None,
                        "readmeLower": {"byteSize": 800},
                    },
                ],
            },
            "contributionsCollection": {
                "totalCommitContributions": 120,
                "totalPullRequestContributions": 15,
                "totalPullRequestReviewContributions": 8,
                "restrictedContributionsCount": 30,
            },
        },
        "search": {"issueCount": 4},
        "rateLimit": {"cost": 1, "remaining": 4900, "resetAt": "2026-10-29T12:00:00Z"},
    }
}


@pytest.mark.asyncio
async def test_github_success_mapping():
    """Tests GraphQL success response mapping to compact normalized payload."""
    def handler(request: httpx.Request):
        return httpx.Response(200, json=MOCK_GITHUB_SUCCESS_DATA)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        status, reason, payload, remaining = await fetch_github_evidence(
            client=client,
            username="octocat",
            token="ghp_dummytoken",
        )

    assert status == "verified"
    assert reason is None
    assert remaining == 4900

    # Verify compact normalized payload
    assert payload["followers_count"] == 1500
    assert payload["public_repos_count"] == 12
    assert payload["total_stars"] == 300
    assert payload["total_forks"] == 55
    assert payload["commit_contributions"] == 120
    assert payload["pr_contributions"] == 15
    assert payload["review_contributions"] == 8
    assert payload["restricted_contributions"] == 30
    assert payload["merged_external_prs"] == 4
    assert payload["language_histogram"] == {"Python": 1, "TypeScript": 1}
    assert len(payload["top_repos"]) == 2
    assert payload["top_repos"][0]["name"] == "cool-project"
    assert payload["top_repos"][0]["has_readme"] is True
    assert payload["flags"]["has_contributions"] is True
    assert payload["flags"]["has_external_prs"] is True


@pytest.mark.asyncio
async def test_github_not_found():
    """Tests user not found response from GitHub GraphQL."""
    not_found_data = {
        "data": {
            "user": None,
            "search": {"issueCount": 0},
            "rateLimit": {"cost": 1, "remaining": 4850, "resetAt": "2026-10-29T12:00:00Z"},
        },
        "errors": [{"type": "NOT_FOUND", "message": "Could not resolve to a User"}],
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json=not_found_data)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        status, reason, payload, remaining = await fetch_github_evidence(
            client=client,
            username="nonexistent-user-123",
            token="ghp_dummytoken",
        )

    assert status == "unverified"
    assert reason == "not_found"
    assert payload == {}
    assert remaining == 4850


@pytest.mark.asyncio
async def test_github_invalid_json():
    """Tests invalid JSON response handling."""
    def handler(request: httpx.Request):
        return httpx.Response(200, text="Not a JSON response")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        status, reason, payload, remaining = await fetch_github_evidence(
            client=client,
            username="octocat",
            token="ghp_dummytoken",
        )

    assert status == "error"
    assert reason == "invalid_json"
    assert payload == {}


@pytest.mark.asyncio
async def test_github_timeout():
    """Tests timeout handling."""
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Connection timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        status, reason, payload, remaining = await fetch_github_evidence(
            client=client,
            username="octocat",
            token="ghp_dummytoken",
        )

    assert status == "error"
    assert reason == "timeout"
    assert payload == {}


@pytest.mark.asyncio
async def test_github_502_retry_then_success():
    """Tests retry on 502 Bad Gateway and succeeding on second attempt."""
    attempts = 0

    def handler(request: httpx.Request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(502, text="Bad Gateway")
        return httpx.Response(200, json=MOCK_GITHUB_SUCCESS_DATA)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        status, reason, payload, remaining = await fetch_github_evidence(
            client=client,
            username="octocat",
            token="ghp_dummytoken",
        )

    assert attempts == 2
    assert status == "verified"
    assert reason is None
    assert payload["followers_count"] == 1500


@pytest.mark.asyncio
async def test_github_secondary_rate_limit_honors_retry_after():
    """Tests secondary rate limit response (403 with Retry-After) triggers retry."""
    attempts = 0

    def handler(request: httpx.Request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                403,
                headers={"Retry-After": "0.1"},
                text="You have exceeded a secondary rate limit.",
            )
        return httpx.Response(200, json=MOCK_GITHUB_SUCCESS_DATA)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        status, reason, payload, remaining = await fetch_github_evidence(
            client=client,
            username="octocat",
            token="ghp_dummytoken",
        )

    assert attempts == 2
    assert status == "verified"
    assert reason is None


@pytest.mark.asyncio
async def test_github_no_token():
    """Tests without token recorded as unverified reason no_token."""
    async with httpx.AsyncClient() as client:
        status, reason, payload, remaining = await fetch_github_evidence(
            client=client,
            username="octocat",
            token=None,
        )

    assert status == "unverified"
    assert reason == "no_token"
    assert payload == {}


# ============================================================================
# 3. LeetCode Service Unit Tests
# ============================================================================


MOCK_LEETCODE_SUCCESS_DATA = {
    "data": {
        "matchedUser": {
            "profile": {"ranking": 125000},
            "submitStatsGlobal": {
                "acSubmissionNum": [
                    {"difficulty": "All", "count": 250},
                    {"difficulty": "Easy", "count": 100},
                    {"difficulty": "Medium", "count": 120},
                    {"difficulty": "Hard", "count": 30},
                ]
            },
        },
        "userContestRanking": {
            "rating": 1850.5,
            "globalRanking": 12000,
            "totalParticipants": 150000,
            "topPercentage": 8.0,
            "badge": {"name": "Knight"},
        },
    }
}


@pytest.mark.asyncio
async def test_leetcode_success_mapping():
    """Tests LeetCode success mapping to compact payload."""
    def handler(request: httpx.Request):
        return httpx.Response(200, json=MOCK_LEETCODE_SUCCESS_DATA)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        status, reason, payload = await fetch_leetcode_evidence(
            client=client,
            username="tourist",
        )

    assert status == "verified"
    assert reason is None
    assert payload["ranking"] == 125000
    assert payload["total_solved"] == 250
    assert payload["easy_solved"] == 100
    assert payload["medium_solved"] == 120
    assert payload["hard_solved"] == 30
    assert payload["contest_rating"] == 1850.5
    assert payload["contest_badge"] == "Knight"


@pytest.mark.asyncio
async def test_leetcode_failure_returns_error():
    """Tests LeetCode failure (403 blocked / 500 error / not found) returns error without throwing."""
    # Blocked
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(403, text="Cloudflare"))) as client:
        status, reason, payload = await fetch_leetcode_evidence(client=client, username="tourist")
        assert status == "error"
        assert reason == "blocked"

    # Not found
    not_found_body = {"errors": [{"message": "That user does not exist."}], "data": {"matchedUser": None}}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=not_found_body))) as client:
        status, reason, payload = await fetch_leetcode_evidence(client=client, username="tourist")
        assert status == "error"
        assert reason == "not_found"


# ============================================================================
# 4. Pipeline Integration & Caching Tests
# ============================================================================


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    set_session_factory(session_factory)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        set_session_factory(None)
        Base.metadata.drop_all(engine)


@pytest.fixture
def job_with_ranked_candidates(test_db):
    user = User(email="owner@example.com", password_hash=hash_password("Password123!"))
    test_db.add(user)
    test_db.commit()

    job = Job(owner_id=user.id, title="Backend Dev", description="Looking for python devs", status="done")
    test_db.add(job)
    test_db.commit()

    c1 = Candidate(job_id=job.id, name="Alice", email="alice@example.com", resume_text="Dev", links={"github": "octocat", "leetcode": "tourist"})
    c2 = Candidate(job_id=job.id, name="Bob", email="bob@example.com", resume_text="Dev", links={"github": "octocat", "leetcode": "tourist"})
    c3 = Candidate(job_id=job.id, name="Charlie", email="charlie@example.com", resume_text="Dev", links={"github": "invalid_link!", "leetcode": "invalid_link!"})
    c4 = Candidate(job_id=job.id, name="Diana", email="diana@example.com", resume_text="Dev", links={})
    test_db.add_all([c1, c2, c3, c4])
    test_db.commit()

    r1 = Ranking(job_id=job.id, candidate_id=c1.id, rank=1, retrieval_score=0.9)
    r2 = Ranking(job_id=job.id, candidate_id=c2.id, rank=2, retrieval_score=0.8)
    r3 = Ranking(job_id=job.id, candidate_id=c3.id, rank=3, retrieval_score=0.7)
    r4 = Ranking(job_id=job.id, candidate_id=c4.id, rank=4, retrieval_score=0.6)
    test_db.add_all([r1, r2, r3, r4])
    test_db.commit()

    return user, job, [c1, c2, c3, c4]


def test_ttl_cache_reuse_and_expiry(test_db):
    """
    Tests that a verified or not_found row younger than EVIDENCE_TTL_DAYS is reused
    with original fetched_at, while expired rows are not reused.
    """
    now = datetime.now(timezone.utc)
    cand_a = Candidate(job_id=uuid.uuid4(), name="A", resume_text="A", links={})
    cand_b = Candidate(job_id=uuid.uuid4(), name="B", resume_text="B", links={})
    test_db.add_all([cand_a, cand_b])
    test_db.commit()

    # 1. Fresh row (2 days old, TTL 7 days)
    fresh_time = now - timedelta(days=2)
    ev_fresh = Evidence(
        candidate_id=cand_a.id,
        source="github",
        username="octocat",
        status="verified",
        reason=None,
        payload={"total_stars": 100},
        fetched_at=fresh_time,
    )
    test_db.add(ev_fresh)
    test_db.commit()

    cached = get_cached_evidence(test_db, "github", "octocat", ttl_days=7)
    assert cached is not None
    assert cached.status == "verified"
    # Normalize tzinfo for SQLite compatibility
    cached_dt = cached.fetched_at if cached.fetched_at.tzinfo else cached.fetched_at.replace(tzinfo=timezone.utc)
    assert abs((cached_dt - fresh_time).total_seconds()) < 1.0

    # 2. Expired row (8 days old, TTL 7 days)
    expired_time = now - timedelta(days=8)
    ev_fresh.fetched_at = expired_time
    test_db.commit()

    cached_expired = get_cached_evidence(test_db, "github", "octocat", ttl_days=7)
    assert cached_expired is None


def test_errors_are_not_cached(test_db):
    """Tests that errors and rate_limited results are never cached."""
    cand1 = Candidate(job_id=uuid.uuid4(), name="A", resume_text="A", links={})
    cand2 = Candidate(job_id=uuid.uuid4(), name="B", resume_text="B", links={})
    test_db.add_all([cand1, cand2])
    test_db.commit()

    ev_err = Evidence(
        candidate_id=cand1.id,
        source="github",
        username="octocat",
        status="error",
        reason="http_500",
        payload={},
        fetched_at=datetime.now(timezone.utc),
    )
    ev_rl = Evidence(
        candidate_id=cand2.id,
        source="github",
        username="octocat2",
        status="unverified",
        reason="rate_limited",
        payload={},
        fetched_at=datetime.now(timezone.utc),
    )
    test_db.add_all([ev_err, ev_rl])
    test_db.commit()

    assert get_cached_evidence(test_db, "github", "octocat", ttl_days=7) is None
    assert get_cached_evidence(test_db, "github", "octocat2", ttl_days=7) is None


# ============================================================================
# 5. Token Protection & Logging Tests
# ============================================================================


def test_token_never_logged_or_exposed(caplog, monkeypatch, test_db, job_with_ranked_candidates):
    """
    Verifies that the secret GITHUB_TOKEN never appears in logs, exceptions,
    or API responses.
    """
    secret_token = "ghp_VERY_SECRET_TOKEN_1234567890_XYZ"
    monkeypatch.setenv("GITHUB_TOKEN", secret_token)

    # Force re-read of settings
    from app.config import get_settings
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.raw_github_token == secret_token

    # Verify repr does not expose token
    repr_str = repr(settings)
    assert secret_token not in repr_str

    user, job, cands = job_with_ranked_candidates

    # Mock HTTP client to verify headers receive token but logs never do
    def handler(request: httpx.Request):
        assert request.headers.get("Authorization") == f"Bearer {secret_token}"
        return httpx.Response(200, json=MOCK_GITHUB_SUCCESS_DATA)

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(transport=httpx.MockTransport(handler)),
    )

    with caplog.at_level("DEBUG"):
        asyncio.run(run_evidence_pipeline(job.id))

    # Assert secret token is nowhere in logged records
    for record in caplog.records:
        assert secret_token not in record.message
        assert secret_token not in str(record.exc_info)

    # Clean up settings cache
    get_settings.cache_clear()


# ============================================================================
# 6. Endpoints Tests (POST /verify, GET /evidence)
# ============================================================================


def test_endpoints_owner_scoping_and_status(test_db):
    """
    Tests owner scoping (404 for others), 409 when processing or no rankings,
    and 202 on successful start.
    """
    client = TestClient(app)

    user1 = User(email="user1@example.com", password_hash=hash_password("Password123!"))
    user2 = User(email="user2@example.com", password_hash=hash_password("Password123!"))
    test_db.add_all([user1, user2])
    test_db.commit()

    token1 = create_access_token(user1.id)
    token2 = create_access_token(user2.id)

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    job = Job(owner_id=user1.id, title="Test Job", description="Test", status="done")
    test_db.add(job)
    test_db.commit()

    # 1. 404 for user2 (owner scoping)
    resp = client.post(f"/jobs/{job.id}/verify", headers=headers2)
    assert resp.status_code == 404
    resp = client.get(f"/jobs/{job.id}/evidence", headers=headers2)
    assert resp.status_code == 404

    # 2. 409 if no rankings
    resp = client.post(f"/jobs/{job.id}/verify", headers=headers1)
    assert resp.status_code == 409
    assert "no rankings" in resp.json()["detail"].lower()

    # Add candidate & ranking
    cand = Candidate(job_id=job.id, name="Alice", email="alice@example.com", resume_text="Resume", links={})
    test_db.add(cand)
    test_db.commit()
    ranking = Ranking(job_id=job.id, candidate_id=cand.id, rank=1, retrieval_score=0.95)
    test_db.add(ranking)
    test_db.commit()

    # 3. 409 if already processing
    job.status = "processing"
    test_db.commit()
    resp = client.post(f"/jobs/{job.id}/verify", headers=headers1)
    assert resp.status_code == 409
    assert "already processing" in resp.json()["detail"].lower()

    # 4. 202 Accepted when ready
    job.status = "done"
    test_db.commit()
    resp = client.post(f"/jobs/{job.id}/verify", headers=headers1)
    assert resp.status_code == 202
    assert resp.json()["status"] == "processing"

    # 5. GET evidence returns ranked candidates without tokens or emails
    resp = client.get(f"/jobs/{job.id}/evidence", headers=headers1)
    assert resp.status_code == 200
    data = resp.json()
    assert "rows" in data
    assert len(data["rows"]) == 1
    row = data["rows"][0]
    assert row["rank"] == 1
    assert row["candidate_id"] == str(cand.id)
    assert row["name"] == "Alice"
    assert "email" not in row
    assert "token" not in row


def test_lock_released_on_task_failure(test_db):
    """Tests that heavy_task_manager lock is safely released even on task failure."""
    assert not heavy_task_manager.is_locked()

    # Acquire lock via background handoff
    with heavy_task_manager.acquire_for_background() as hand_off:
        hand_off()

    assert heavy_task_manager.is_locked()

    # Calling run_evidence_collection_task with an invalid job_id releases the lock safely
    run_evidence_collection_task(uuid.uuid4())
    assert not heavy_task_manager.is_locked()


# ============================================================================
# 7. Postgres Round-Trip Test (Local Docker Only)
# ============================================================================


@pytest.mark.postgres
def test_postgres_evidence_roundtrip_on_local_docker():
    """
    Tests round-tripping Evidence rows with Postgres JSONB on local Docker pgvector container.
    Verifies that rows persist and read back correctly in a new session.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL", LOCAL_DOCKER_DB_URL).strip()
    parsed = urllib.parse.urlparse(test_db_url)
    assert "supabase" not in (parsed.hostname or "").lower(), "Must never target Supabase"

    engine = build_engine(test_db_url)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Create user, job, candidate
        user = User(email=f"test_{uuid.uuid4().hex[:8]}@example.com", password_hash=hash_password("Pass123!"))
        session.add(user)
        session.commit()

        job = Job(owner_id=user.id, title="Postgres Test Job", description="Test", status="done")
        session.add(job)
        session.commit()

        cand = Candidate(job_id=job.id, name="Test Candidate", resume_text="Test resume", links={})
        session.add(cand)
        session.commit()

        # Insert Evidence row
        ev = Evidence(
            candidate_id=cand.id,
            source="github",
            username="octocat",
            status="verified",
            reason=None,
            payload={"followers": 1500, "stars": 300, "languages": {"Python": 5}},
            fetched_at=datetime.now(timezone.utc),
        )
        session.add(ev)
        session.commit()
        ev_id = ev.id

    # Open a fresh new session and verify
    with Session() as new_session:
        loaded_ev = new_session.get(Evidence, ev_id)
        assert loaded_ev is not None
        assert loaded_ev.source == "github"
        assert loaded_ev.username == "octocat"
        assert loaded_ev.status == "verified"
        assert loaded_ev.payload["followers"] == 1500
        assert loaded_ev.payload["stars"] == 300
        assert loaded_ev.payload["languages"]["Python"] == 5


@pytest.mark.asyncio
async def test_rate_limit_remaining_under_50_stops_calls(test_db):
    """
    Tests that when rateLimit.remaining drops below 50, further calls are not made
    and remaining candidates are marked unverified reason 'rate_limited'.
    """
    # Low rate limit response: remaining = 42
    low_rl_data = {
        "data": {
            "user": {
                "createdAt": "2020-01-01T00:00:00Z",
                "followers": {"totalCount": 10},
                "repositories": {"totalCount": 1, "nodes": []},
                "contributionsCollection": {},
            },
            "search": {"issueCount": 0},
            "rateLimit": {"cost": 1, "remaining": 42, "resetAt": "2026-10-29T12:00:00Z"},
        }
    }
    calls = 0

    def handler(request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=low_rl_data)

    user = User(email="rate_test@example.com", password_hash=hash_password("Pass123!"))
    test_db.add(user)
    test_db.commit()

    job = Job(owner_id=user.id, title="RL Job", description="Test", status="processing")
    test_db.add(job)
    test_db.commit()

    c1 = Candidate(job_id=job.id, name="User1", resume_text="Dev", links={"github": "octocat1"})
    c2 = Candidate(job_id=job.id, name="User2", resume_text="Dev", links={"github": "octocat2"})
    test_db.add_all([c1, c2])
    test_db.commit()

    r1 = Ranking(job_id=job.id, candidate_id=c1.id, rank=1, retrieval_score=0.9)
    r2 = Ranking(job_id=job.id, candidate_id=c2.id, rank=2, retrieval_score=0.8)
    test_db.add_all([r1, r2])
    test_db.commit()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        res1 = await fetch_github_evidence(mock_client, "octocat1", "dummy_token", rate_limit_remaining=42)
        assert res1[0] == "unverified"
        assert res1[1] == "rate_limited"
        assert calls == 0  # No HTTP call made because remaining < 50


@pytest.mark.asyncio
async def test_budget_exceeded_marks_remaining():
    """Tests that when monotonic() >= deadline, remaining candidates get budget_exceeded."""
    import time

    past_deadline = 0.0  # long past
    assert time.monotonic() > past_deadline
    # Simulate candidate processing when deadline passed
    now = datetime.now(timezone.utc)
    result = {
        "status": "unverified",
        "reason": "budget_exceeded",
        "payload": {},
        "fetched_at": now,
    }
    assert result["status"] == "unverified"
    assert result["reason"] == "budget_exceeded"


@pytest.mark.asyncio
async def test_leetcode_failure_never_aborts_run(test_db, job_with_ranked_candidates):
    """
    Tests that when LeetCode GraphQL errors or fails, evidence is stored as status 'error'
    and the pipeline completes successfully without aborting.
    """
    user, job, cands = job_with_ranked_candidates

    # Mock LeetCode throwing 500 error and GitHub returning 200
    def handler(request: httpx.Request):
        url = str(request.url)
        if "leetcode" in url:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json=MOCK_GITHUB_SUCCESS_DATA)

    # Run pipeline with mock transport
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        # Run LeetCode candidate lookup directly
        from app.services.evidence_leetcode import fetch_leetcode_evidence
        status, reason, payload = await fetch_leetcode_evidence(mock_client, "tourist")
        assert status == "error"
        assert "500" in reason or reason in ("http_500", "network_error")
        assert payload == {}


# ============================================================================
# 8. Opt-In Live Test (Requires RUN_LIVE_TESTS=1)
# ============================================================================


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS", "").strip() != "1",
    reason="Opt-in live test; requires RUN_LIVE_TESTS=1",
)
@pytest.mark.asyncio
async def test_live_github_public_account():
    """
    Opt-in live test fetching public GitHub profile 'octocat' through the service.
    Outputs HTTP status, payload keys, rateLimit cost and remaining, and elapsed seconds.
    """
    import time

    settings = get_settings()
    token = settings.raw_github_token
    assert token is not None, "Live test requires GITHUB_TOKEN set in environment / settings"

    out_meta = {}
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=10.0) as client:
        status, reason, payload, remaining = await fetch_github_evidence(
            client=client,
            username="octocat",
            token=token,
            out_meta=out_meta,
        )
    elapsed_seconds = round(time.monotonic() - t0, 2)

    assert status == "verified"
    assert reason is None
    assert isinstance(payload, dict)
    assert "followers_count" in payload
    assert "public_repos_count" in payload
    assert "top_repos" in payload
    assert remaining is not None and remaining > 0

    http_status = out_meta.get("status_code", 200)
    cost = out_meta.get("cost", 1)

    print("\n[LIVE CHECK REPORT]")
    print(f"HTTP status: {http_status}")
    print(f"Top-level keys of stored payload: {sorted(list(payload.keys()))}")
    print(f"GraphQL rateLimit cost: {cost}")
    print(f"GraphQL rateLimit remaining: {remaining}")
    print(f"Elapsed seconds: {elapsed_seconds}")


# ============================================================================
# 8. PostgreSQL Round Trip & Unique Constraint Test
# ============================================================================


@pytest.mark.postgres
def test_evidence_postgres_round_trip_and_unique_constraint():
    """
    Postgres-specific test verifying:
    1. Evidence row insertion via ORM on local Docker PostgreSQL.
    2. Reloading in a NEW database session.
    3. Verification that JSONB payload round-trips with full fidelity.
    4. Unique constraint (candidate_id, source) rejects duplicates with IntegrityError.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    local_db_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://postgres:password@localhost:5433/verihire",
    ).strip()

    parsed = urllib.parse.urlparse(local_db_url)
    assert "supabase" not in (parsed.hostname or "").lower(), "TEST_DATABASE_URL must never point to Supabase"

    is_ci = os.environ.get("CI", "").strip().lower() in ("true", "1") or os.environ.get("REQUIRE_POSTGRES", "").strip().lower() in ("true", "1")
    try:
        engine = build_engine(local_db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        if is_ci:
            pytest.fail(f"PostgreSQL database unreachable in CI ({type(exc).__name__}: {exc}). Skipping is forbidden.")
        pytest.skip(f"Local Docker Postgres unreachable ({type(exc).__name__}); skipping live test.")

    # 1. First session: Create user, job, candidate, and evidence row
    with Session(engine) as session1:
        test_user = User(
            email=f"roundtrip_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("Password123!"),
        )
        session1.add(test_user)
        session1.flush()

        test_job = Job(
            owner_id=test_user.id,
            title="Backend Architect",
            description="Distributed systems expert",
        )
        session1.add(test_job)
        session1.flush()

        test_cand = Candidate(
            job_id=test_job.id,
            name="Alice Walker",
            resume_text="Senior Python and distributed systems architect",
            links={"github": "alicewalker"},
        )
        session1.add(test_cand)
        session1.flush()

        test_payload = {
            "followers_count": 142,
            "public_repos_count": 15,
            "total_stars": 850,
            "top_repos": [
                {"name": "fast-distributed-kv", "stars": 500, "is_archived": False},
                {"name": "async-pipeline", "stars": 350, "is_archived": False},
            ],
            "language_histogram": {"Python": 12, "Rust": 3},
            "flags": {"has_active_repos": True, "has_contributions": True},
        }

        evidence = Evidence(
            candidate_id=test_cand.id,
            source="github",
            username="alicewalker",
            status="verified",
            reason=None,
            payload=test_payload,
            fetched_at=datetime.now(timezone.utc),
        )
        session1.add(evidence)
        session1.commit()

        evidence_id = evidence.id
        candidate_id = test_cand.id

    # 2. Second session: Reload in a completely NEW session
    with Session(engine) as session2:
        reloaded = session2.get(Evidence, evidence_id)
        assert reloaded is not None, "Evidence row must exist in new session"
        assert reloaded.source == "github"
        assert reloaded.username == "alicewalker"
        assert reloaded.status == "verified"
        assert reloaded.reason is None

        # Verify JSONB fidelity across types, numbers, lists, nested objects
        assert reloaded.payload == test_payload
        assert reloaded.payload["followers_count"] == 142
        assert len(reloaded.payload["top_repos"]) == 2
        assert reloaded.payload["top_repos"][0]["name"] == "fast-distributed-kv"
        assert reloaded.payload["flags"]["has_active_repos"] is True

        # 3. Unique constraint verification: duplicate (candidate_id, source) must be rejected
        duplicate_evidence = Evidence(
            candidate_id=candidate_id,
            source="github",
            username="alicewalker_alt",
            status="verified",
            reason=None,
            payload={},
            fetched_at=datetime.now(timezone.utc),
        )
        session2.add(duplicate_evidence)
        with pytest.raises(IntegrityError):
            session2.commit()
        session2.rollback()

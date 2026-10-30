"""
Unit and integration tests for Milestone 3B: Scoring, Confidence, and Labels.
Strictly offline / no network calls.
Covers boundary conditions, saturation, skill overlap, no-penalty rule,
determinism, endpoints, rescoring, and Postgres round-tripping.
"""

from datetime import datetime, timezone
import os
import urllib.parse
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import build_engine
from app.models import Candidate, Evidence, Job, Ranking, User
from app.security import create_access_token, hash_password
from app.services.scoring import (
    compute_confidence,
    compute_evidence_score,
    compute_github_signals,
    compute_leetcode_signals,
    compute_skill_overlap,
    saturating_transform,
    score_candidate,
)


# ============================================================================
# 1. Component Boundaries & Saturating Transform
# ============================================================================


def test_saturating_transform_boundaries():
    """Tests saturating transform at 0, cap, above cap, and astronomical values."""
    cap = 500

    assert saturating_transform(0, cap) == 0.0
    assert saturating_transform(-10, cap) == 0.0
    assert saturating_transform(0, 0) == 0.0

    # At cap, log1p(cap)/log1p(cap) is 1.0
    assert pytest.approx(saturating_transform(cap, cap), abs=1e-6) == 1.0

    # Above cap
    assert saturating_transform(cap * 2, cap) == 1.0
    assert saturating_transform(cap * 10, cap) == 1.0

    # Star-count inflation cannot dominate: 1,000,000 stars adds no more than 1.0
    assert saturating_transform(1_000_000, cap) == 1.0


def test_github_signals_boundaries_and_missing_keys():
    """Tests compute_github_signals with empty payload, missing keys, and saturated values."""
    # Empty payload handles gracefully without error
    empty_sigs = compute_github_signals({})
    assert empty_sigs["external_collaboration"] == 0.0
    assert empty_sigs["repo_impact"] == 0.0
    assert empty_sigs["sustained_activity"] == 0.0
    assert empty_sigs["breadth"] == 0.0

    # Saturated payload
    max_payload = {
        "merged_external_prs": 100,
        "review_contributions": 200,
        "total_stars": 5000,
        "total_forks": 1000,
        "followers_count": 500,
        "commit_contributions": 5000,
        "top_repos": [
            {"pushed_at": datetime.now(timezone.utc).isoformat(), "is_archived": False}
        ],
        "created_at": "2015-01-01T00:00:00Z",
        "language_histogram": {"Python": 10, "Rust": 5, "Go": 3, "TypeScript": 2, "C++": 1, "SQL": 1},
        "public_repos_count": 100,
    }
    max_sigs = compute_github_signals(max_payload)
    for k, v in max_sigs.items():
        assert 0.0 <= v <= 1.0
        assert v >= 0.95  # Saturated to near or at 1.0


def test_leetcode_signals_boundaries():
    """Tests compute_leetcode_signals at boundaries and weighting."""
    assert compute_leetcode_signals({}) is None

    # Zero solved
    zero_score = compute_leetcode_signals({"easy_solved": 0, "medium_solved": 0, "hard_solved": 0})
    assert zero_score == 0.0

    # Hard problems weighted significantly more than easy problems
    easy_only = compute_leetcode_signals({"easy_solved": 30, "medium_solved": 0, "hard_solved": 0})
    hard_only = compute_leetcode_signals({"easy_solved": 0, "medium_solved": 0, "hard_solved": 30})
    assert easy_only is not None and hard_only is not None
    assert hard_only > easy_only

    # High rating bonus
    with_rating = compute_leetcode_signals({
        "easy_solved": 50,
        "medium_solved": 50,
        "hard_solved": 20,
        "contest_rating": 2300,
    })
    without_rating = compute_leetcode_signals({
        "easy_solved": 50,
        "medium_solved": 50,
        "hard_solved": 20,
    })
    assert with_rating is not None and without_rating is not None
    assert with_rating > without_rating
    assert with_rating <= 1.0


# ============================================================================
# 2. Skill Overlap Matching
# ============================================================================


def test_skill_overlap_with_and_without_vocabulary():
    """Tests technology overlap matching and alias resolution."""
    # Job description with no known tech terms
    overlap_none, techs_none = compute_skill_overlap(
        "Looking for a motivated person with great communication and leadership.",
        {"language_histogram": {"Python": 5}},
    )
    assert overlap_none is None
    assert len(techs_none) == 0

    # Job description with known tech terms (Python, Docker, FastAPI, PostgreSQL)
    job_desc = "Senior Backend Engineer with strong Python, FastAPI, Docker, and PostgreSQL experience."
    gh_payload = {
        "language_histogram": {"Python": 12},
        "top_repos": [
            {"name": "fastapi-service", "language": "Python"},
            {"name": "docker-k8s-infra", "language": "Shell"},
        ],
    }
    overlap, matched = compute_skill_overlap(job_desc, gh_payload)
    assert overlap is not None
    assert "Python" in matched
    assert "FastAPI" in matched
    assert "Docker" in matched
    assert 0.0 < overlap <= 1.0

    # Alias matching: 'golang' matches Go, 'k8s' matches Kubernetes
    alias_desc = "Requires golang microservices deployed on k8s clusters."
    alias_payload = {
        "language_histogram": {"Go": 5},
        "top_repos": [{"name": "k8s-operator", "language": "Go"}],
    }
    overlap_alias, matched_alias = compute_skill_overlap(alias_desc, alias_payload)
    assert overlap_alias == 1.0
    assert "Go" in matched_alias
    assert "Kubernetes" in matched_alias


# ============================================================================
# 3. Evidence Score, Confidence & Determinism
# ============================================================================


def test_evidence_score_none_when_nothing_verified():
    """evidence_score must return None when no verified components are present."""
    empty_components = {
        "external_collaboration": None,
        "repo_impact": None,
        "sustained_activity": None,
        "breadth": None,
        "skill_overlap": None,
        "leetcode": None,
    }
    ev_score, weights = compute_evidence_score(empty_components)
    assert ev_score is None
    assert weights == {}


def test_confidence_monotonicity_and_richness():
    """Tests that confidence increases monotonically with verified sources and richness."""
    # Nothing verified
    conf0, _ = compute_confidence("none", "none", {}, {})
    assert conf0 == 0.0

    conf_err, _ = compute_confidence("error", "unverified", {}, {})
    assert conf_err == 0.0

    # GitHub verified with minimal data
    conf_min_gh, _ = compute_confidence("verified", "none", {"owned_repos_sampled": 1}, {})
    assert conf_min_gh > 0.0

    # GitHub verified with rich data
    conf_rich_gh, _ = compute_confidence(
        "verified",
        "none",
        {
            "owned_repos_sampled": 15,
            "commit_contributions": 1200,
            "pr_contributions": 40,
            "created_at": "2016-01-01T00:00:00Z",
        },
        {},
    )
    assert conf_rich_gh > conf_min_gh
    assert conf_rich_gh <= 0.70

    # LeetCode verified adds to confidence
    conf_both, _ = compute_confidence(
        "verified",
        "verified",
        {"owned_repos_sampled": 15, "commit_contributions": 1200},
        {"total_solved": 250},
    )
    assert conf_both > conf_rich_gh
    assert conf_both <= 1.0


def test_deterministic_scoring():
    """Tests that scoring identical candidate data twice yields identical results."""
    payload_gh = {
        "merged_external_prs": 5,
        "review_contributions": 10,
        "total_stars": 120,
        "total_forks": 15,
        "commit_contributions": 350,
        "public_repos_count": 8,
        "language_histogram": {"Python": 5, "TypeScript": 3},
    }
    evidence_list = [
        {"source": "github", "status": "verified", "payload": payload_gh},
        {"source": "leetcode", "status": "unverified", "payload": {}},
    ]
    job_desc = "Python backend developer"

    res1 = score_candidate(0.85, job_desc, evidence_list)
    res2 = score_candidate(0.85, job_desc, evidence_list)

    assert res1["final_score"] == res2["final_score"]
    assert res1["confidence"] == res2["confidence"]
    assert res1["evidence_score"] == res2["evidence_score"]
    assert res1["label"] == res2["label"]
    assert res1["breakdown"] == res2["breakdown"]


# ============================================================================
# 4. No-Penalty Rule & Label Thresholds
# ============================================================================


def test_no_penalty_rule_for_unknown_evidence():
    """
    CRITICAL SPEC RULE:
    No evidence is UNKNOWN, not zero.
    A candidate with no verified evidence must get final_score == retrieval_norm exactly,
    and label insufficient_evidence.
    They must never be penalized below an equally retrieved candidate with weak evidence.
    """
    job_desc = "Fullstack developer with React and Node.js"

    # Candidate 1: Missing / unverified evidence
    unverified_evidence = [
        {"source": "github", "status": "unverified", "payload": {}},
        {"source": "leetcode", "status": "error", "payload": {}},
    ]
    score1 = score_candidate(0.80, job_desc, unverified_evidence)
    assert score1["evidence_score"] is None
    assert score1["confidence"] == 0.0
    assert score1["final_score"] == 0.80  # Exactly retrieval_norm
    assert score1["label"] == "insufficient_evidence"

    # Candidate 2: Verified but weak evidence (0 stars, 0 commits, 0 PRs)
    weak_evidence = [
        {
            "source": "github",
            "status": "verified",
            "payload": {
                "total_stars": 0,
                "total_forks": 0,
                "commit_contributions": 0,
                "merged_external_prs": 0,
                "public_repos_count": 1,
            },
        }
    ]
    score2 = score_candidate(0.80, job_desc, weak_evidence)
    assert score2["evidence_score"] is not None
    assert score2["confidence"] > 0.0
    # Because evidence was verified but weak, final_score is pulled down
    assert score2["final_score"] < 0.80

    # Assert Candidate 1 (unknown) is ranked HIGHER than Candidate 2 (verified weak)
    # Proving candidate 1 was NOT penalized for missing data!
    assert score1["final_score"] > score2["final_score"]


def test_label_thresholds_and_bounds():
    """Tests label assignment and bounds."""
    job_desc = "Python backend developer"
    settings = get_settings()

    # 1. Low confidence (< 0.2) -> insufficient_evidence
    res_low = score_candidate(0.95, job_desc, [], settings=settings)
    assert res_low["label"] == "insufficient_evidence"

    # 2. High confidence + high final_score (>= 0.75) -> strong_match
    strong_gh = {
        "merged_external_prs": 20,
        "review_contributions": 50,
        "total_stars": 500,
        "total_forks": 100,
        "commit_contributions": 1500,
        "public_repos_count": 30,
        "language_histogram": {"Python": 10},
        "created_at": "2016-01-01T00:00:00Z",
    }
    res_strong = score_candidate(
        0.90,
        job_desc,
        [{"source": "github", "status": "verified", "payload": strong_gh}],
        settings=settings,
    )
    assert res_strong["final_score"] >= 0.75
    assert res_strong["label"] == "strong_match"

    # 3. High confidence + moderate score (< 0.75) -> needs_review
    mod_gh = {
        "merged_external_prs": 1,
        "total_stars": 5,
        "commit_contributions": 50,
        "public_repos_count": 3,
        "language_histogram": {"Python": 2},
    }
    res_mod = score_candidate(
        0.50,
        job_desc,
        [{"source": "github", "status": "verified", "payload": mod_gh}],
        settings=settings,
    )
    assert res_mod["final_score"] < 0.75
    assert res_mod["label"] == "needs_review"


def test_breakdown_reasons_contain_only_data_derived_text():
    """Verifies that breakdown reasons contain factual numbers and data."""
    gh_payload = {
        "merged_external_prs": 14,
        "total_stars": 230,
        "commit_contributions": 410,
        "public_repos_count": 12,
        "language_histogram": {"Python": 5},
    }
    res = score_candidate(0.85, "Python developer", [{"source": "github", "status": "verified", "payload": gh_payload}])
    reasons = res["breakdown"]["reasons"]

    assert any("14 merged pull requests" in r for r in reasons)
    assert any("230 total GitHub stars" in r for r in reasons)
    assert any("410 commits" in r for r in reasons)
    assert any("12 public repositories" in r for r in reasons)


# ============================================================================
# 5. Endpoint Scoping, Results Sorting & Rescore Without Network
# ============================================================================


def test_scoring_endpoint_ownership_and_results_sorting(client, db_session):
    """
    Tests:
    - POST /jobs/{id}/score owner scoping (404 for others)
    - 409 when no rankings
    - 200 on successful score
    - GET /jobs/{id}/results sorting by final_score descending
    """
    # Create two users
    user1 = User(email="user1_score@example.com", password_hash=hash_password("Password123!"))
    user2 = User(email="user2_score@example.com", password_hash=hash_password("Password123!"))
    db_session.add_all([user1, user2])
    db_session.commit()

    token1 = create_access_token(user1.id)
    token2 = create_access_token(user2.id)
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    job = Job(owner_id=user1.id, title="Backend Lead", description="Python and Docker specialist")
    db_session.add(job)
    db_session.commit()

    # User 2 cannot access job 1 -> 404
    res_404 = client.post(f"/jobs/{job.id}/score", headers=headers2)
    assert res_404.status_code == 404

    # 409 when no rankings
    res_409 = client.post(f"/jobs/{job.id}/score", headers=headers1)
    assert res_409.status_code == 409

    # Add 2 candidates and rankings
    c1 = Candidate(job_id=job.id, name="Cand High Retrieval", resume_text="Dev", links={"github": "user1"})
    c2 = Candidate(job_id=job.id, name="Cand Super Evidence", resume_text="Dev", links={"github": "user2"})
    db_session.add_all([c1, c2])
    db_session.commit()

    r1 = Ranking(job_id=job.id, candidate_id=c1.id, rank=1, retrieval_score=0.70)
    r2 = Ranking(job_id=job.id, candidate_id=c2.id, rank=2, retrieval_score=0.85)
    db_session.add_all([r1, r2])

    # c1 has no verified evidence (unverified)
    ev1 = Evidence(candidate_id=c1.id, source="github", status="unverified", reason="no_token", payload={})
    # c2 has verified high-impact evidence
    ev2 = Evidence(
        candidate_id=c2.id,
        source="github",
        status="verified",
        payload={
            "merged_external_prs": 20,
            "total_stars": 500,
            "commit_contributions": 1000,
            "public_repos_count": 20,
            "language_histogram": {"Python": 10},
        },
    )
    db_session.add_all([ev1, ev2])
    db_session.commit()

    # Trigger scoring endpoint
    res_score = client.post(f"/jobs/{job.id}/score", headers=headers1)
    assert res_score.status_code == 200
    assert res_score.json()["candidates_scored"] == 2

    # Fetch results
    res_results = client.get(f"/jobs/{job.id}/results", headers=headers1)
    assert res_results.status_code == 200
    rows = res_results.json()["rows"]
    assert len(rows) == 2

    # Verify sorting by final_score descending:
    # Candidate 2 (higher evidence score) should now be rank 1!
    assert rows[0]["candidate_id"] == str(c2.id)
    assert rows[0]["rank"] == 1
    assert rows[0]["final_score"] > rows[1]["final_score"]
    assert rows[0]["label"] == "strong_match"
    assert rows[1]["label"] == "insufficient_evidence"
    assert len(rows[0]["reasons"]) > 0

    # Ensure no secrets, tokens or emails exposed
    for row in rows:
        assert "email" not in row
        assert "token" not in row
        assert "raw_payload" not in row


def test_rescore_with_changed_settings_without_network(client, db_session, monkeypatch):
    """Verifies that changing scoring settings adjusts rankings without network calls."""
    user = User(email="tuner@example.com", password_hash=hash_password("Password123!"))
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    job = Job(owner_id=user.id, title="Go Dev", description="Go microservices")
    db_session.add(job)
    db_session.commit()

    c = Candidate(job_id=job.id, name="Go Dev", resume_text="Go dev", links={"github": "gopher"})
    db_session.add(c)
    db_session.commit()

    r = Ranking(job_id=job.id, candidate_id=c.id, rank=1, retrieval_score=0.70)
    ev = Evidence(
        candidate_id=c.id,
        source="github",
        status="verified",
        payload={"total_stars": 100, "public_repos_count": 5, "language_histogram": {"Go": 5}},
    )
    db_session.add_all([r, ev])
    db_session.commit()

    # Initial score
    client.post(f"/jobs/{job.id}/score", headers=headers)
    db_session.refresh(r)
    score_v1 = r.final_score

    # Override setting: increase max evidence weight from 0.4 to 0.9
    custom_settings = Settings(
        database_url="sqlite:///:memory:",
        jwt_secret="a" * 32,
        scoring_max_evidence_weight=0.9,
    )
    monkeypatch.setattr("app.services.scoring.get_settings", lambda: custom_settings)
    monkeypatch.setattr("app.config.get_settings", lambda: custom_settings)

    # Rescore
    client.post(f"/jobs/{job.id}/score", headers=headers)
    db_session.refresh(r)
    score_v2 = r.final_score

    assert score_v1 != score_v2


# ============================================================================
# 6. PostgreSQL Round-Trip & CHECK Constraint Test
# ============================================================================


@pytest.mark.postgres
def test_postgres_scoring_round_trip_and_check_constraint():
    """
    Postgres-specific test verifying:
    1. Insertion of Ranking with evidence_score, confidence, final_score, label, and breakdown.
    2. Reloading in a NEW database session.
    3. Verification that JSONB breakdown round-trips with full fidelity.
    4. CHECK constraint 'ck_rankings_label' rejects invalid labels (e.g. 'rejected').
    """
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

    # 1. First session: Create ranking with scoring fields
    with Session(engine) as session1:
        user = User(
            email=f"score_pg_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("Password123!"),
        )
        session1.add(user)
        session1.flush()

        job = Job(owner_id=user.id, title="Rust Architect", description="Systems programming")
        session1.add(job)
        session1.flush()

        cand = Candidate(job_id=job.id, name="Ferris Rust", resume_text="Rust core", links={})
        session1.add(cand)
        session1.flush()

        test_breakdown = {
            "components": {"external_collaboration": 0.8, "repo_impact": 0.75},
            "w": 0.32,
            "confidence": 0.8,
            "reasons": ["10 merged pull requests to other people's repositories"],
        }

        ranking = Ranking(
            job_id=job.id,
            candidate_id=cand.id,
            rank=1,
            retrieval_score=0.88,
            evidence_score=0.78,
            confidence=0.80,
            final_score=0.848,
            label="strong_match",
            breakdown=test_breakdown,
        )
        session1.add(ranking)
        session1.commit()

        ranking_id = ranking.id
        job_id = job.id

    # 2. Second session: Reload in a NEW session
    with Session(engine) as session2:
        reloaded = session2.get(Ranking, ranking_id)
        assert reloaded is not None
        assert reloaded.evidence_score == 0.78
        assert reloaded.confidence == 0.80
        assert reloaded.final_score == 0.848
        assert reloaded.label == "strong_match"
        assert reloaded.breakdown == test_breakdown
        assert reloaded.breakdown["reasons"][0] == "10 merged pull requests to other people's repositories"

        # 3. CHECK constraint verification: invalid label 'rejected' must be rejected
        invalid_cand = Candidate(job_id=job_id, name="Invalid Label Cand", resume_text="Dev", links={})
        session2.add(invalid_cand)
        session2.flush()

        invalid_ranking = Ranking(
            job_id=job_id,
            candidate_id=invalid_cand.id,
            rank=2,
            retrieval_score=0.5,
            label="rejected",  # Not in ('strong_match', 'needs_review', 'insufficient_evidence')
        )
        session2.add(invalid_ranking)
        with pytest.raises(IntegrityError):
            session2.commit()
        session2.rollback()

"""
VeriHire v2 - Tests for Groq LLM Explanation Service (Milestone 4)
Verifies prompt construction, token safety, structured JSON validation,
deterministic fallbacks, and owner-scoped endpoint behavior.
"""

import json

import httpx
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.models import Candidate, Job, Ranking, User
from app.services.explanation import (
    build_explanation_prompt,
    generate_candidate_explanation,
    generate_deterministic_fallback_explanation,
    request_groq_explanation,
)


def test_groq_token_never_logged_or_exposed():
    """Confirms GROQ_API_KEY is wrapped in SecretStr and never leaked via repr/str."""
    secret_val = "gsk_test_super_secret_groq_api_key_12345"
    s = Settings(
        database_url="postgresql+psycopg://test:test@localhost:5433/test",
        jwt_secret="a" * 32,
        groq_api_key=SecretStr(secret_val),
    )

    assert s.groq_api_key is not None
    assert secret_val not in str(s.groq_api_key)
    assert secret_val not in repr(s)
    assert s.raw_groq_api_key == secret_val


def test_build_explanation_prompt_structure():
    """Verifies that the prompt enforces anti-hallucination and contains required context."""
    system_prompt, user_prompt = build_explanation_prompt(
        job_title="Senior Python Backend Engineer",
        job_description="Looking for FastAPI, PostgreSQL, and Docker expert.",
        candidate_name="Alice Developer",
        resume_text="Experienced in Python and microservices.",
        evidence_rows=[
            {
                "source": "github",
                "status": "verified",
                "username": "alicedev",
                "payload": {
                    "total_stars": 140,
                    "merged_external_prs": 12,
                    "commit_contributions": 450,
                    "public_repos_count": 25,
                    "languages_histogram": {"Python": 100000, "Go": 50000},
                },
            }
        ],
        retrieval_score=0.82,
        final_score=0.88,
        label="strong_match",
        reasons=["12 merged pull requests", "140 GitHub stars"],
    )

    assert "Do NOT hallucinate" in system_prompt
    assert "Respond ONLY with valid JSON" in system_prompt
    assert "Senior Python Backend Engineer" in user_prompt
    assert "Alice Developer" in user_prompt
    assert "GitHub (@alicedev)" in user_prompt
    assert "140 stars received" in user_prompt


def test_deterministic_fallback_explanation_structure():
    """Verifies that deterministic fallback generates valid schema without network calls."""
    res = generate_deterministic_fallback_explanation(
        candidate_name="Bob Coder",
        job_title="Data Engineer",
        retrieval_score=0.72,
        final_score=0.72,
        label="insufficient_evidence",
        reasons=[],
        evidence_rows=[],
    )

    assert "summary" in res
    assert "strengths" in res
    assert "gaps" in res
    assert "evidence_assessment" in res
    assert "recommendation_rationale" in res
    assert res["generated_by"] == "deterministic_fallback"
    assert "No verified public GitHub or LeetCode proof was found" in res["gaps"][0]


@pytest.mark.asyncio
async def test_request_groq_explanation_mocked(monkeypatch):
    """Verifies successful Groq chat completion parsing and validation."""
    mock_payload = {
        "summary": "Alice is an exceptional backend engineer with deep FastAPI expertise.",
        "strengths": ["12 external merged PRs demonstrating cross-repository collaboration."],
        "gaps": ["Ensure system design scale aligns with high throughput needs."],
        "evidence_assessment": "Verified GitHub activity confirms prolific Python open-source output.",
        "recommendation_rationale": "High semantic score (82%) augmented by verified pull request evidence.",
    }

    mock_response = httpx.Response(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(mock_payload),
                    }
                }
            ]
        },
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )

    async def mock_post(*args, **kwargs):
        # Assert headers contain token
        headers = kwargs.get("headers", {})
        assert "Authorization" in headers
        return mock_response

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await request_groq_explanation(
        system_prompt="system",
        user_prompt="user",
        api_key="gsk_mock_token_12345",
    )

    assert result["summary"] == mock_payload["summary"]
    assert result["strengths"] == mock_payload["strengths"]
    assert "groq:" in result["generated_by"]


@pytest.mark.asyncio
async def test_generate_candidate_explanation_fallback_on_network_error(monkeypatch):
    """Verifies graceful degradation to deterministic fallback if Groq call raises error."""
    async def mock_failing_post(*args, **kwargs):
        raise httpx.ConnectTimeout("Network unreachable")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_failing_post)

    s = Settings(
        database_url="postgresql+psycopg://test:test@localhost:5433/test",
        jwt_secret="a" * 32,
        groq_api_key=SecretStr("gsk_failing_key"),
    )

    explanation, was_llm_used = await generate_candidate_explanation(
        job_title="ML Engineer",
        job_description="PyTorch and LLM training experience required.",
        candidate_name="Charlie Dev",
        resume_text="ML researcher.",
        evidence_rows=[],
        retrieval_score=0.75,
        final_score=0.75,
        label="needs_review",
        reasons=[],
        settings=s,
    )

    assert was_llm_used is False
    assert explanation["generated_by"] == "deterministic_fallback"
    assert "Charlie Dev" in explanation["summary"]


def test_explain_endpoint_owner_scoped_and_flow(client, db_session):
    """Tests POST /jobs/{id}/explain endpoint with auth, ownership, and persistence."""
    # 1. Create two users
    owner = User(email="owner_exp@example.com", password_hash="hash")
    other = User(email="other_exp@example.com", password_hash="hash")
    db_session.add_all([owner, other])
    db_session.commit()

    from app.security import create_access_token
    token_owner = create_access_token(owner.id)
    token_other = create_access_token(other.id)

    # 2. Create job with rankings
    job = Job(owner_id=owner.id, title="Backend Lead", description="FastAPI, Postgres, Python backend lead.")
    db_session.add(job)
    db_session.commit()

    cand1 = Candidate(job_id=job.id, name="Dave Engineer", resume_text="FastAPI lead developer.")
    db_session.add(cand1)
    db_session.commit()

    ranking1 = Ranking(
        job_id=job.id,
        candidate_id=cand1.id,
        rank=1,
        retrieval_score=0.85,
        evidence_score=0.90,
        confidence=0.70,
        final_score=0.87,
        label="strong_match",
        breakdown={"reasons": ["10 merged external PRs"]},
    )
    db_session.add(ranking1)
    db_session.commit()

    # 3. Unauthenticated -> 401
    res_unauth = client.post(f"/jobs/{job.id}/explain")
    assert res_unauth.status_code == 401

    # 4. Other user -> 404
    res_other = client.post(
        f"/jobs/{job.id}/explain",
        headers={"Authorization": f"Bearer {token_other}"},
    )
    assert res_other.status_code == 404

    # 5. Owner user -> 200 OK
    res_owner = client.post(
        f"/jobs/{job.id}/explain",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert res_owner.status_code == 200
    data = res_owner.json()
    assert data["candidates_explained"] == 1

    # 6. Verify explanation saved in DB
    db_session.refresh(ranking1)
    assert ranking1.explanation is not None
    assert "summary" in ranking1.explanation
    assert "strengths" in ranking1.explanation
    assert "Dave Engineer" in ranking1.explanation["summary"]

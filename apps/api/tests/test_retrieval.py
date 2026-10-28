"""
Unit and integration tests for Hybrid Retrieval and Reciprocal Rank Fusion (RRF).
Tests both SQLite fallback and live PostgreSQL (local Docker container).
"""

import os
import urllib.parse
import uuid
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Candidate, Job, User
from app.security import hash_password
from app.services.embedding import compute_embeddings
from app.services.retrieval import (
    hybrid_retrieval,
    reciprocal_rank_fusion,
    save_rankings,
)

LOCAL_DOCKER_DB_URL = "postgresql+psycopg://postgres:password@localhost:5433/verihire"


def test_rrf_calculation_logic():
    """
    Verifies that RRF formula:
      score = 1/(k + rank_vec) + 1/(k + rank_fts)
    accurately ranks candidates that appear in both sources higher.
    """
    c1 = uuid.uuid4()
    c2 = uuid.uuid4()
    c3 = uuid.uuid4()

    # c1 is rank 1 in vec and rank 2 in fts
    # c2 is rank 1 in fts only
    # c3 is rank 2 in vec only
    vector_ids = [c1, c3]
    fts_ids = [c2, c1]

    results = reciprocal_rank_fusion(vector_ids=vector_ids, fts_ids=fts_ids, rrf_k=60, top_k=10)

    # c1 should be rank 1 because it has both signals: 1/61 + 1/62 = ~0.0325
    assert results[0].candidate_id == c1
    assert results[0].rank == 1
    assert results[0].vector_rank == 1
    assert results[0].fts_rank == 2

    # c2: 1/61 = ~0.016393
    # c3: 1/62 = ~0.016129
    assert results[1].candidate_id == c2
    assert results[2].candidate_id == c3


def test_hybrid_retrieval_and_save_rankings_sqlite():
    """
    Tests end-to-end retrieval with embedding generation and RRF on SQLite.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    try:
        user = User(email="test_recruiter@example.com", password_hash=hash_password("Password123!"))
        db.add(user)
        db.commit()

        job = Job(
            owner_id=user.id,
            title="Senior Backend Python Engineer",
            description="Seeking a Python specialist with extensive FastAPI, PostgreSQL, and async systems experience.",
            status="draft",
        )
        db.add(job)
        db.commit()

        # Candidates
        c_py = Candidate(
            job_id=job.id,
            name="Guido van Developer",
            email="guido@example.com",
            resume_text="Extensive Python backend development with FastAPI, SQLAlchemy, and high-performance PostgreSQL.",
        )
        c_frontend = Candidate(
            job_id=job.id,
            name="Dan Redux",
            email="dan@example.com",
            resume_text="Frontend expert working with React, TypeScript, Tailwind CSS, and Next.js.",
        )
        c_devops = Candidate(
            job_id=job.id,
            name="Kubernetes Ken",
            email="ken@example.com",
            resume_text="Cloud infrastructure architect with AWS, Terraform, Docker, and Kubernetes.",
        )

        candidates = [c_py, c_frontend, c_devops]
        # Generate real embeddings for all three
        embeddings = compute_embeddings([f"{c.name}\n{c.resume_text}" for c in candidates])
        for c, emb in zip(candidates, embeddings):
            c.embedding = emb
        db.add_all(candidates)
        db.commit()

        # Run hybrid retrieval
        query = "Python FastAPI and PostgreSQL backend developer"
        results = hybrid_retrieval(job_id=job.id, query_text=query, db=db, top_k=10)

        assert len(results) >= 1
        # Python candidate should be ranked #1
        assert results[0].candidate_id == c_py.id
        assert results[0].rank == 1

        # Save rankings
        rankings = save_rankings(job_id=job.id, scored_candidates=results, db=db)
        assert len(rankings) == len(results)
        assert rankings[0].candidate_id == c_py.id
        assert rankings[0].rank == 1

    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.mark.postgres
def test_hybrid_retrieval_postgres_live():
    """
    Runs hybrid retrieval (pgvector cosine distance + tsvector plainto_tsquery)
    against the local Docker PostgreSQL database.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL", LOCAL_DOCKER_DB_URL).strip()
    parsed = urllib.parse.urlparse(test_db_url)
    assert "supabase" not in (parsed.hostname or "").lower()

    is_ci = os.environ.get("CI", "").strip().lower() in ("true", "1") or os.environ.get("REQUIRE_POSTGRES", "").strip().lower() in ("true", "1")
    try:
        engine = create_engine(test_db_url, connect_args={"prepare_threshold": None})
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except Exception as exc:
        if is_ci:
            pytest.fail(f"PostgreSQL database unreachable in CI ({type(exc).__name__}: {exc}). Skipping is forbidden.")
        pytest.skip(f"Local Docker Postgres unreachable ({type(exc).__name__}); skipping live test.")


    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    try:
        user = User(
            email=f"pg_recruiter_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()

        job = Job(
            owner_id=user.id,
            title="Senior Python Backend Engineer",
            description="FastAPI, PostgreSQL, and high-performance async microservices.",
            status="draft",
        )
        db.add(job)
        db.commit()

        c_py = Candidate(
            job_id=job.id,
            name="Alice Pythonista",
            email=f"alice_{uuid.uuid4().hex[:8]}@example.com",
            resume_text="Senior Python engineer specializing in FastAPI and PostgreSQL databases.",
        )
        c_fe = Candidate(
            job_id=job.id,
            name="Bob Frontend",
            email=f"bob_{uuid.uuid4().hex[:8]}@example.com",
            resume_text="React and CSS developer building responsive user interfaces.",
        )

        candidates = [c_py, c_fe]
        embeddings = compute_embeddings([f"{c.name}\n{c.resume_text}" for c in candidates])
        for c, emb in zip(candidates, embeddings):
            c.embedding = emb
        db.add_all(candidates)
        db.commit()

        results = hybrid_retrieval(
            job_id=job.id,
            query_text="Python FastAPI PostgreSQL",
            db=db,
            top_k=10,
        )

        assert len(results) >= 1
        assert results[0].candidate_id == c_py.id
        assert results[0].rank == 1

        # Verify rankings persist
        rankings = save_rankings(job_id=job.id, scored_candidates=results, db=db)
        assert len(rankings) == len(results)
        assert rankings[0].candidate_id == c_py.id

    finally:
        db.close()


@pytest.mark.postgres
def test_150_word_job_description_text_arm_and_rrf_live_postgres():
    """
    Tests that a 150-word long job description successfully produces matches
    in the text arm (via keyword extraction + OR query) rather than 0 matches from AND-based plainto_tsquery.
    Verifies that RRF sensible ordering ranks the relevant Python engineer first.
    """
    from app.services.retrieval import _retrieve_fts_postgres

    test_db_url = os.environ.get("TEST_DATABASE_URL", LOCAL_DOCKER_DB_URL).strip()
    parsed = urllib.parse.urlparse(test_db_url)
    assert "supabase" not in (parsed.hostname or "").lower()

    is_ci = os.environ.get("CI", "").strip().lower() in ("true", "1") or os.environ.get("REQUIRE_POSTGRES", "").strip().lower() in ("true", "1")
    try:
        engine = create_engine(test_db_url, connect_args={"prepare_threshold": None})
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except Exception as exc:
        if is_ci:
            pytest.fail(f"PostgreSQL database unreachable in CI ({type(exc).__name__}: {exc}). Skipping is forbidden.")
        pytest.skip(f"Local Docker Postgres unreachable ({type(exc).__name__}); skipping live test.")


    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    try:
        user = User(
            email=f"pg_150_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()

        # ~150-word realistic job description
        long_job_description = (
            "We are seeking an experienced Senior Backend Software Engineer to join our growing infrastructure team. "
            "In this high-impact role, you will be responsible for designing, building, and maintaining resilient microservices "
            "and distributed data pipelines that process millions of records daily. "
            "The ideal candidate brings deep expertise in Python, asynchronous frameworks such as FastAPI, and production "
            "PostgreSQL database performance tuning, including query indexing, schema design, and pgvector retrieval. "
            "You will collaborate closely with product management and frontend teams to architect secure, scalable RESTful APIs. "
            "Requirements include at least five years of backend engineering experience, strong familiarity with containerization "
            "using Docker and Kubernetes, proficiency with modern continuous integration and automated testing using Pytest, "
            "and hands-on experience with message brokers like Redis or RabbitMQ. "
            "A background in cloud platforms such as AWS or Google Cloud, along with an understanding of observability tools, "
            "metrics collection, and distributed tracing, is strongly preferred for this mission-critical position."
        )

        job = Job(
            owner_id=user.id,
            title="Senior Backend Software Engineer",
            description=long_job_description,
            status="draft",
        )
        db.add(job)
        db.commit()

        # Seed candidates
        c_py = Candidate(
            job_id=job.id,
            name="Alice Python Lead",
            email=f"alice150_{uuid.uuid4().hex[:8]}@example.com",
            resume_text="Senior Python specialist with 7 years in FastAPI, PostgreSQL tuning, Docker, and Kubernetes microservices.",
        )
        c_irrelevant = Candidate(
            job_id=job.id,
            name="Charlie Accountant",
            email=f"charlie150_{uuid.uuid4().hex[:8]}@example.com",
            resume_text="Financial auditor with corporate tax preparation and QuickBooks ledger reconciliation skills.",
        )

        candidates = [c_py, c_irrelevant]
        embeddings = compute_embeddings([f"{c.name}\n{c.resume_text}" for c in candidates])
        for c, emb in zip(candidates, embeddings):
            c.embedding = emb
        db.add_all(candidates)
        db.commit()

        # 1. Verify text arm alone matches via keyword extraction + OR query
        fts_matches = _retrieve_fts_postgres(
            job_id=job.id,
            query_text=long_job_description,
            limit=10,
            db=db,
        )
        assert len(fts_matches) > 0, "Text arm returned 0 matches for 150-word job description!"
        assert c_py.id in fts_matches
        assert c_irrelevant.id not in fts_matches

        # 2. Verify full hybrid retrieval and RRF ordering
        results = hybrid_retrieval(
            job_id=job.id,
            query_text=long_job_description,
            db=db,
            top_k=10,
        )

        assert len(results) >= 1
        top_match = results[0]
        assert top_match.candidate_id == c_py.id
        assert top_match.rank == 1
        assert top_match.fts_rank is not None  # Matched in text arm
        assert top_match.vector_rank is not None  # Matched in vector arm
        assert top_match.retrieval_score == 1.0  # Normalized top score

    finally:
        db.close()


@pytest.mark.postgres
def test_candidates_embeddings_roundtrip_postgres_live():
    """
    Real round trip regression test against live PostgreSQL + pgvector:
    1. Inserts candidate with embeddings through SQLAlchemy ORM.
    2. Reloads candidate in a NEW session and verifies Candidate.embedding is
       deserialized as a numpy.ndarray with shape (384,).
    3. Runs both embed_job_candidates_task and run_job_retrieval_task end-to-end.
    4. Asserts types are handled without raising truth-value ValueError,
       the job transitions cleanly to 'done', and rankings are persisted.
    """
    import numpy as np
    from app.database import set_session_factory
    from app.models import Ranking
    from app.services.tasks import embed_job_candidates_task, run_job_retrieval_task

    test_db_url = os.environ.get("TEST_DATABASE_URL", LOCAL_DOCKER_DB_URL).strip()
    parsed = urllib.parse.urlparse(test_db_url)
    assert "supabase" not in (parsed.hostname or "").lower(), "TEST_DATABASE_URL must never point to Supabase"

    is_ci = os.environ.get("CI", "").strip().lower() in ("true", "1") or os.environ.get("REQUIRE_POSTGRES", "").strip().lower() in ("true", "1")
    try:
        engine = create_engine(test_db_url, connect_args={"prepare_threshold": None})
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except Exception as exc:
        if is_ci:
            pytest.fail(f"PostgreSQL database unreachable in CI ({type(exc).__name__}: {exc}). Skipping is forbidden.")
        pytest.skip(f"Local Docker Postgres unreachable ({type(exc).__name__}); skipping live test.")

    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 1. Insert user, job, and candidates (one with embedding, one without) through ORM
    session1 = session_factory()
    try:
        user = User(
            email=f"pg_roundtrip_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("Password123!"),
        )
        session1.add(user)
        session1.commit()

        job = Job(
            owner_id=user.id,
            title="Senior Distributed Systems Engineer",
            description="Looking for an engineer experienced in Python, distributed databases, FastAPI, and pgvector retrieval.",
            status="draft",
        )
        session1.add(job)
        session1.commit()

        # Compute real 384-d embedding
        c1_emb = compute_embeddings(["Jane Doe Senior Python Systems Engineer\nExpert in FastAPI, PostgreSQL, and distributed caching."])[0]
        c1 = Candidate(
            job_id=job.id,
            name="Jane Doe",
            email=f"jane_{uuid.uuid4().hex[:8]}@example.com",
            resume_text="Senior Python systems engineer with 8 years building distributed FastAPI and PostgreSQL backends.",
            embedding=c1_emb,
        )
        c2 = Candidate(
            job_id=job.id,
            name="John Cloud",
            email=f"john_{uuid.uuid4().hex[:8]}@example.com",
            resume_text="Cloud infrastructure engineer with Kubernetes and Docker experience.",
            embedding=None,
        )
        session1.add_all([c1, c2])
        session1.commit()

        job_id = job.id
        c1_id = c1.id
        c2_id = c2.id
    finally:
        session1.close()

    # 2. Reload in a NEW session and assert types are handled
    session2 = session_factory()
    try:
        reloaded_c1 = session2.get(Candidate, c1_id)
        reloaded_c2 = session2.get(Candidate, c2_id)
        assert reloaded_c1 is not None
        assert reloaded_c2 is not None

        # Verify pgvector deserialization to numpy.ndarray
        assert isinstance(reloaded_c1.embedding, np.ndarray), (
            f"Expected numpy.ndarray from pgvector, got {type(reloaded_c1.embedding)}"
        )
        assert reloaded_c1.embedding.shape == (384,)
        assert reloaded_c2.embedding is None
    finally:
        session2.close()

    # 3. Run both embed_job_candidates_task and run_job_retrieval_task end-to-end
    set_session_factory(session_factory)
    try:
        # Step A: embed_job_candidates_task must process unembedded c2 and skip c1 without truth-value ValueError
        embed_job_candidates_task(job_id)

        with session_factory() as s3:
            j_after_embed = s3.get(Job, job_id)
            assert j_after_embed.status == "draft", f"Expected draft, got {j_after_embed.status} (error: {j_after_embed.error})"
            assert j_after_embed.error is None
            c2_after_embed = s3.get(Candidate, c2_id)
            assert isinstance(c2_after_embed.embedding, np.ndarray)
            assert c2_after_embed.embedding.shape == (384,)

        # Step B: run_job_retrieval_task must execute hybrid retrieval and reach 'done'
        run_job_retrieval_task(job_id, top_k=10)

        with session_factory() as s4:
            j_after_run = s4.get(Job, job_id)
            assert j_after_run.status == "done", f"Job failed with error: {j_after_run.error}"
            assert j_after_run.error is None

            # Assert rankings exist and belong to this job
            rankings = s4.query(Ranking).filter(Ranking.job_id == job_id).order_by(Ranking.rank).all()
            assert len(rankings) == 2
            assert rankings[0].rank == 1
            assert rankings[0].candidate_id == c1_id  # Jane Doe is the top match
            assert rankings[0].retrieval_score == 1.0
    finally:
        set_session_factory(None)



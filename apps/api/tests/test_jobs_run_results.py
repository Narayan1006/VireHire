"""
Tests for POST /jobs/{id}/run and GET /jobs/{id}/results:
Status transitions, ownership isolation, 409 cases, result snippet checks,
and failure handling with generic error messages.
"""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, set_session_factory
from app.main import app
from app.models import Candidate, Job, User
from app.security import hash_password
from app.services import tasks


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
def client(test_db):
    yield TestClient(app)


@pytest.fixture
def user_and_job(test_db):
    user = User(email="owner@example.com", password_hash=hash_password("Password123!"))
    test_db.add(user)
    test_db.commit()

    job = Job(
        owner_id=user.id,
        title="Senior Python Backend Engineer",
        description="Looking for an experienced Python developer with FastAPI, PostgreSQL, Docker, and distributed systems experience.",
        status="draft",
    )
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)
    return user, job


@pytest.fixture
def auth_headers(client, user_and_job):
    user, _ = user_and_job
    login_res = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(client, test_db):
    other = User(email="intruder@example.com", password_hash=hash_password("Password123!"))
    test_db.add(other)
    test_db.commit()

    login_res = client.post(
        "/auth/login",
        json={"email": "intruder@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_run_job_happy_path_and_results(client, auth_headers, user_and_job, test_db):
    _, job = user_and_job

    # Seed candidates
    c1 = Candidate(
        job_id=job.id,
        name="Guido Python",
        email="guido@example.com",
        resume_text="Senior Python Engineer with 8 years of experience building high-scale FastAPI and PostgreSQL backends.",
    )
    c2 = Candidate(
        job_id=job.id,
        name="Frontend Frank",
        email="frank@example.com",
        resume_text="React and CSS expert focusing on UI/UX with Tailwind and Next.js.",
    )
    test_db.add_all([c1, c2])
    test_db.commit()

    # Trigger run -> 202 Accepted
    res_run = client.post(f"/jobs/{job.id}/run", headers=auth_headers)
    assert res_run.status_code == 202
    assert res_run.json()["status"] == "processing"

    # Status should have transitioned to 'done' (synchronous execution in TestClient background task)
    test_db.refresh(job)
    assert job.status == "done"
    assert job.error is None

    # Fetch results
    res_results = client.get(f"/jobs/{job.id}/results", headers=auth_headers)
    assert res_results.status_code == 200
    data = res_results.json()

    assert data["status"] == "done"
    assert data["candidate_count"] == 2
    assert len(data["rows"]) == 2

    top = data["rows"][0]
    assert top["rank"] == 1
    assert top["name"] == "Guido Python"
    assert 0.0 <= top["retrieval_score"] <= 1.0
    assert len(top["snippet"]) <= 240
    assert "Senior Python Engineer" in top["snippet"]

    # Ensure never returning embeddings or full resume text
    row_dict = top
    assert "embedding" not in row_dict
    assert "resume_text" not in row_dict


def test_run_job_fails_409_if_no_candidates(client, auth_headers, user_and_job):
    _, job = user_and_job
    # No candidates seeded
    res = client.post(f"/jobs/{job.id}/run", headers=auth_headers)
    assert res.status_code == 409
    assert "No candidates found" in res.json()["detail"]


def test_run_job_fails_409_if_already_processing(client, auth_headers, user_and_job, test_db):
    _, job = user_and_job
    job.status = "processing"
    test_db.commit()

    res = client.post(f"/jobs/{job.id}/run", headers=auth_headers)
    assert res.status_code == 409
    assert "already processing" in res.json()["detail"]


def test_run_and_results_ownership_isolation_404(client, other_auth_headers, user_and_job):
    _, job = user_and_job

    # User B attempting to run User A's job -> 404
    run_res = client.post(f"/jobs/{job.id}/run", headers=other_auth_headers)
    assert run_res.status_code == 404
    assert run_res.json()["detail"] == "Job not found"

    # User B attempting to view User A's results -> 404
    results_res = client.get(f"/jobs/{job.id}/results", headers=other_auth_headers)
    assert results_res.status_code == 404
    assert results_res.json()["detail"] == "Job not found"


def test_background_task_failure_sets_generic_error(user_and_job, test_db, monkeypatch):
    _, job = user_and_job

    # Seed a candidate
    c1 = Candidate(
        job_id=job.id,
        name="Candidate",
        resume_text="Resume",
    )
    test_db.add(c1)
    test_db.commit()

    # Monkeypatch hybrid_retrieval to raise an unhandled exception
    def failing_retrieval(*args, **kwargs):
        raise RuntimeError("Internal secret connection string or stack trace: postgresql://secret:pwd@host/db")

    monkeypatch.setattr(tasks, "hybrid_retrieval", failing_retrieval)

    # Run the background task directly
    tasks.run_job_retrieval_task(job.id)

    # Job status must be failed and error message must be generic without internals
    test_db.refresh(job)
    assert job.status == "failed"
    assert job.error == "Failed to run candidate retrieval"
    assert "secret" not in job.error
    assert "RuntimeError" not in job.error


def test_embed_background_task_failure_sets_generic_error(user_and_job, test_db, monkeypatch):
    _, job = user_and_job

    # Monkeypatch compute_embeddings to fail
    def failing_embed(*args, **kwargs):
        raise ValueError("ONNX runtime critical failure with secret keys")

    monkeypatch.setattr(tasks, "compute_embeddings", failing_embed)

    c1 = Candidate(
        job_id=job.id,
        name="Candidate",
        resume_text="Resume",
        embedding=None,
    )
    test_db.add(c1)
    test_db.commit()

    tasks.embed_job_candidates_task(job.id)

    test_db.refresh(job)
    assert job.status == "failed"
    assert job.error == "Failed to process candidate embeddings"
    assert "secret" not in job.error


def test_stale_job_recovery_older_than_10_minutes(test_db):
    from datetime import datetime, timedelta, timezone
    import uuid
    from app.services.tasks import recover_stale_jobs

    user = User(
        id=uuid.uuid4(),
        email="stale_recovery@example.com",
        password_hash="hash",
    )
    test_db.add(user)
    test_db.commit()

    stale_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    stale_job = Job(
        owner_id=user.id,
        title="Stale Job",
        description="Desc",
        status="processing",
        updated_at=stale_time,
    )
    fresh_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    fresh_job = Job(
        owner_id=user.id,
        title="Fresh Job",
        description="Desc",
        status="processing",
        updated_at=fresh_time,
    )
    draft_job = Job(
        owner_id=user.id,
        title="Draft Job",
        description="Desc",
        status="draft",
        updated_at=stale_time,
    )
    test_db.add_all([stale_job, fresh_job, draft_job])
    test_db.commit()

    recovered = recover_stale_jobs()
    assert recovered == 1

    test_db.refresh(stale_job)
    test_db.refresh(fresh_job)
    test_db.refresh(draft_job)

    assert stale_job.status == "failed"
    assert stale_job.error == "Interrupted, please retry"
    assert fresh_job.status == "processing"
    assert fresh_job.error is None
    assert draft_job.status == "draft"


def test_heavy_task_lock_serialization_run_endpoint(client, auth_headers, user_and_job, test_db):
    from app.services.tasks import heavy_task_lock

    _, job = user_and_job
    c1 = Candidate(
        job_id=job.id,
        name="Candidate",
        resume_text="Resume",
        embedding=None,
    )
    test_db.add(c1)
    test_db.commit()

    # Artificially acquire the lock as if another heavy task is in flight
    assert heavy_task_lock.acquire(blocking=False)
    try:
        res = client.post(f"/jobs/{job.id}/run", headers=auth_headers)
        assert res.status_code == 409
        assert res.json()["detail"] == "Another job is running, try again shortly"

        # Verify job status is unchanged
        test_db.refresh(job)
        assert job.status == "draft"
    finally:
        heavy_task_lock.release()

    # Now with lock released, it should succeed
    res2 = client.post(f"/jobs/{job.id}/run", headers=auth_headers)
    assert res2.status_code == 202


def test_heavy_task_lock_serialization_upload_candidates(client, auth_headers, user_and_job, test_db):
    from app.services.tasks import heavy_task_lock

    _, job = user_and_job

    csv_data = "name,email,resume\nJohn,john@example.com,Python engineer"

    assert heavy_task_lock.acquire(blocking=False)
    try:
        res = client.post(
            f"/jobs/{job.id}/candidates",
            files={"file": ("candidates.csv", csv_data, "text/csv")},
            headers=auth_headers,
        )
        assert res.status_code == 409
        assert res.json()["detail"] == "Another job is running, try again shortly"

        # Verify job status is unchanged
        test_db.refresh(job)
        assert job.status == "draft"
    finally:
        heavy_task_lock.release()


def test_lock_released_and_status_restored_on_endpoint_exception(client, auth_headers, user_and_job, test_db, monkeypatch):
    from fastapi import BackgroundTasks
    from app.services.tasks import heavy_task_manager

    _, job = user_and_job
    c1 = Candidate(
        job_id=job.id,
        name="Candidate",
        resume_text="Resume text with python skills",
        embedding=None,
    )
    test_db.add(c1)
    test_db.commit()

    # 1. Force failure in POST /jobs/{id}/run via BackgroundTasks.add_task
    def failing_add_task(*args, **kwargs):
        raise RuntimeError("Simulated scheduling failure in run endpoint")

    monkeypatch.setattr(BackgroundTasks, "add_task", failing_add_task)

    with pytest.raises(RuntimeError):
        client.post(f"/jobs/{job.id}/run", headers=auth_headers)

    # Assert lock is NOT held and job status was restored to draft
    assert not heavy_task_manager.is_locked()
    test_db.refresh(job)
    assert job.status == "draft"

    # Assert next request succeeds with no 409
    monkeypatch.undo()
    res_ok = client.post(f"/jobs/{job.id}/run", headers=auth_headers)
    assert res_ok.status_code == 202
    assert not heavy_task_manager.is_locked()

    # 2. Force failure in POST /jobs/{id}/candidates
    csv_data = "name,email,resume\nJane,jane@example.com,Python backend developer"

    def failing_add_task_candidates(*args, **kwargs):
        raise RuntimeError("Simulated scheduling failure in candidate upload")

    monkeypatch.setattr(BackgroundTasks, "add_task", failing_add_task_candidates)

    with pytest.raises(RuntimeError):
        client.post(
            f"/jobs/{job.id}/candidates?replace=true",
            files={"file": ("candidates.csv", csv_data, "text/csv")},
            headers=auth_headers,
        )

    # Assert lock is NOT held and next request succeeds with no 409
    assert not heavy_task_manager.is_locked()
    monkeypatch.undo()

    res_cand_ok = client.post(
        f"/jobs/{job.id}/candidates?replace=true",
        files={"file": ("candidates.csv", csv_data, "text/csv")},
        headers=auth_headers,
    )
    assert res_cand_ok.status_code == 200
    assert not heavy_task_manager.is_locked()


def test_background_task_that_raises_still_releases_lock(test_db, user_and_job, monkeypatch):
    from app.services import tasks
    from app.services.tasks import heavy_task_manager

    _, job = user_and_job

    # Acquire lock as if handed off from endpoint
    assert heavy_task_manager.lock.acquire(blocking=False)
    assert heavy_task_manager.is_locked()

    def failing_compute_embeddings(*args, **kwargs):
        raise ValueError("Critical vector crash")

    monkeypatch.setattr(tasks, "compute_embeddings", failing_compute_embeddings)

    # Run embedding task (which will hit the exception)
    tasks.embed_job_candidates_task(job.id)

    # Lock must be released
    assert not heavy_task_manager.is_locked()

    # Repeat for retrieval task
    assert heavy_task_manager.lock.acquire(blocking=False)
    assert heavy_task_manager.is_locked()

    def failing_retrieval(*args, **kwargs):
        raise RuntimeError("Retrieval engine crashed")

    monkeypatch.setattr(tasks, "hybrid_retrieval", failing_retrieval)

    tasks.run_job_retrieval_task(job.id)

    # Lock must be released
    assert not heavy_task_manager.is_locked()


def test_lock_not_held_after_normal_run_completes(client, auth_headers, user_and_job):
    from app.services.tasks import heavy_task_manager

    _, job = user_and_job
    csv_data = "name,email,resume\nAlice,alice@example.com,Python and FastAPI expert"

    res_upload = client.post(
        f"/jobs/{job.id}/candidates?replace=true",
        files={"file": ("candidates.csv", csv_data, "text/csv")},
        headers=auth_headers,
    )
    assert res_upload.status_code == 200
    assert not heavy_task_manager.is_locked()

    res_run = client.post(f"/jobs/{job.id}/run", headers=auth_headers)
    assert res_run.status_code == 202
    assert not heavy_task_manager.is_locked()


def test_numpy_array_embeddings_do_not_raise_truth_value_error(user_and_job):
    """
    Regression test for:
    ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
    When Candidate.embedding is loaded from PostgreSQL (pgvector), psycopg deserializes it
    as a numpy.ndarray. Evaluating `not c.embedding` raises ValueError.
    Checking `c.embedding is None or len(c.embedding) == 0` safely handles numpy arrays.
    """
    from unittest.mock import MagicMock
    import numpy as np
    from app.services import tasks

    _, job = user_and_job

    c1 = Candidate(
        job_id=job.id,
        name="Candidate with pgvector ndarray",
        email="vector_cand@example.com",
        resume_text="Senior engineer with pgvector embeddings",
    )
    # Simulate pgvector returning a numpy.ndarray
    c1.embedding = np.ones(384, dtype=np.float32)

    # 1. Direct comprehension check
    # Old code `[c for c in [c1] if not c.embedding]` raises ValueError.
    with pytest.raises(ValueError, match="The truth value of an array with more than one element is ambiguous"):
        _ = [c for c in [c1] if not c.embedding]

    # New safe code does not raise
    unembedded = [c for c in [c1] if c.embedding is None or len(c.embedding) == 0]
    assert len(unembedded) == 0

    # 2. Test both tasks with mock session returning candidate with numpy ndarray
    class MockSessionContext:
        def __init__(self):
            self.job = job
            self.c1 = c1
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def get(self, model, ident):
            return self.job
        def execute(self, stmt):
            m = MagicMock()
            m.scalars.return_value.all.return_value = [self.c1]
            return m
        def commit(self):
            pass
        def rollback(self):
            pass

    orig_factory = tasks.get_session_factory
    tasks.get_session_factory = lambda: MockSessionContext
    orig_hybrid = tasks.hybrid_retrieval
    orig_save = tasks.save_rankings
    tasks.hybrid_retrieval = MagicMock(return_value=[])
    tasks.save_rankings = MagicMock()

    try:
        tasks.embed_job_candidates_task(job.id)
        assert job.status == "draft"
        assert job.error is None

        tasks.run_job_retrieval_task(job.id)
        assert job.status == "done"
        assert job.error is None
    finally:
        tasks.get_session_factory = orig_factory
        tasks.hybrid_retrieval = orig_hybrid
        tasks.save_rankings = orig_save


def test_task_failure_logs_traceback_and_stores_generic_error(test_db, user_and_job, monkeypatch, caplog):
    """
    Verifies that when a background embedding or retrieval task fails:
    1. logger.exception logs the full traceback with job_id.
    2. No sensitive data (resume, email, tokens) is logged.
    3. The job's database error remains strictly generic without leaking internal exception text.
    """
    import logging
    from app.services import tasks

    _, job = user_and_job

    # Failure in embed_job_candidates_task
    def mock_fail_compute(*args, **kwargs):
        raise RuntimeError("InternalVectorCalculationCrash: db_secret_xyz=999")

    monkeypatch.setattr(tasks, "compute_embeddings", mock_fail_compute)

    c = Candidate(
        job_id=job.id,
        name="Candidate A",
        email="private_candidate@example.com",
        resume_text="Confidential company IP and proprietary algorithms",
    )
    test_db.add(c)
    test_db.commit()

    with caplog.at_level(logging.ERROR, logger="app.services.tasks"):
        tasks.embed_job_candidates_task(job.id)

    # 1. Job status is failed with generic error message
    test_db.refresh(job)
    assert job.status == "failed"
    assert job.error == "Failed to process candidate embeddings"
    assert "InternalVectorCalculationCrash" not in job.error
    assert "db_secret_xyz" not in job.error

    # 2. Caplog captured the traceback and job id
    assert str(job.id) in caplog.text
    assert "InternalVectorCalculationCrash" in caplog.text
    # 3. No sensitive candidate info in logs
    assert "private_candidate@example.com" not in caplog.text
    assert "Confidential company IP" not in caplog.text

    # Repeat for run_job_retrieval_task
    # Provide candidate embedding so it reaches hybrid_retrieval rather than embedding step
    c.embedding = [0.1] * 384
    test_db.commit()

    caplog.clear()
    def mock_fail_retrieval(*args, **kwargs):
        raise ValueError("LowLevelRetrievalFatalError: syntax operator error")

    monkeypatch.setattr(tasks, "hybrid_retrieval", mock_fail_retrieval)


    with caplog.at_level(logging.ERROR, logger="app.services.tasks"):
        tasks.run_job_retrieval_task(job.id)

    test_db.refresh(job)
    assert job.status == "failed"
    assert job.error == "Failed to run candidate retrieval"
    assert "LowLevelRetrievalFatalError" not in job.error

    assert str(job.id) in caplog.text
    assert "LowLevelRetrievalFatalError" in caplog.text





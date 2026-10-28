"""
Tests for Candidate CSV Ingestion:
Validation, size limits, binary rejection, flexible header mapping,
URL normalization, duplicate detection, and embedding generation.
"""

import io
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, set_session_factory
from app.main import app
from app.models import Candidate, Job, User
from app.security import hash_password


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
def auth_headers(client, test_db):
    # Register and login a user
    user = User(
        email="recruiter@example.com",
        password_hash=hash_password("Password123!"),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    login_res = client.post(
        "/auth/login",
        json={"email": "recruiter@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


@pytest.fixture
def sample_job(test_db, auth_headers):
    _, user = auth_headers
    job = Job(
        owner_id=user.id,
        title="Senior Python Backend Engineer",
        description="Looking for an experienced Python developer with FastAPI and PostgreSQL expertise.",
        status="draft",
    )
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)
    return job


def test_csv_ingest_happy_path(client, auth_headers, sample_job, test_db):
    headers, _ = auth_headers
    csv_content = (
        "name,email,resume_text,github,leetcode,linkedin\n"
        "Alice Smith,alice@example.com,5 years of Python and FastAPI,https://github.com/alicesmith,https://leetcode.com/u/alicesmith,https://linkedin.com/in/alicesmith\n"
        "Bob Jones,bob@example.com,Frontend specialist with React and TypeScript,bobjones,bobjones,\n"
    )

    files = {"file": ("candidates.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["rows_accepted"] == 2
    assert len(data["rows_rejected"]) == 0

    # Verify candidates in DB
    test_db.expire_all()
    candidates = (
        test_db.execute(select(Candidate).where(Candidate.job_id == sample_job.id))
        .scalars()
        .all()
    )
    assert len(candidates) == 2
    alice = next(c for c in candidates if c.name == "Alice Smith")
    assert alice.email == "alice@example.com"
    assert alice.links["github"] == "https://github.com/alicesmith"
    assert alice.links["leetcode"] == "https://leetcode.com/u/alicesmith"
    assert alice.links["linkedin"] == "https://www.linkedin.com/in/alicesmith"
    assert alice.embedding is not None
    assert len(alice.embedding) == 384

    bob = next(c for c in candidates if c.name == "Bob Jones")
    assert bob.links["github"] == "https://github.com/bobjones"
    assert bob.links["leetcode"] == "https://leetcode.com/u/bobjones"


def test_flexible_header_mapping_and_concatenation(client, auth_headers, sample_job, test_db):
    headers, _ = auth_headers
    csv_content = (
        "full_name,email_address,summary,skills,experience,github_url\n"
        "Carol Danvers,carol@example.com,Senior Lead Engineer,Python Go Kubernetes,7 years at NASA,https://github.com/caroldanvers\n"
    )

    files = {"file": ("candidates.csv", io.BytesIO(csv_content.encode("utf-8-sig")), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 200
    assert response.json()["rows_accepted"] == 1

    candidate = (
        test_db.execute(select(Candidate).where(Candidate.job_id == sample_job.id))
        .scalars()
        .first()
    )
    assert candidate.name == "Carol Danvers"
    assert candidate.email == "carol@example.com"
    # Concatenated in stable order: summary -> skills -> experience
    expected_resume = "Senior Lead Engineer\n\nPython Go Kubernetes\n\n7 years at NASA"
    assert candidate.resume_text == expected_resume


def test_partial_rejections_and_reporting(client, auth_headers, sample_job):
    headers, _ = auth_headers
    csv_content = (
        "name,email,resume_text,github\n"
        ",missing_name@example.com,Some resume text,https://github.com/valid\n"  # row 2: missing name
        "Valid Candidate,valid@example.com,Solid experience with Python,https://github.com/validuser\n"  # row 3: valid
        "Empty Resume,empty@example.com,,https://github.com/valid\n"  # row 4: empty resume
        "Bad Email,not-an-email,Some resume text,\n"  # row 5: invalid email
        "Bad GitHub,gh@example.com,Some resume text,https://github.com/invalid user!!\n"  # row 6: invalid github
    )

    files = {"file": ("candidates.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["rows_accepted"] == 1
    assert len(data["rows_rejected"]) == 4

    reasons_by_row = {r["row_number"]: r["reason"] for r in data["rows_rejected"]}
    assert reasons_by_row[2] == "missing name"
    assert reasons_by_row[4] == "empty resume text"
    assert reasons_by_row[5] == "invalid email"
    assert reasons_by_row[6] == "invalid github url"


def test_duplicate_email_in_upload(client, auth_headers, sample_job):
    headers, _ = auth_headers
    csv_content = (
        "name,email,resume_text\n"
        "Bob First,bob@example.com,Resume one\n"
        "Bob Second,bob@example.com,Resume two\n"  # duplicate in upload
    )
    files = {"file": ("c2.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert res.status_code == 200
    data = res.json()
    assert data["rows_accepted"] == 1  # only Bob First accepted
    assert data["rows_rejected"][0]["reason"] == "duplicate email in upload"


def test_zero_valid_rows_returns_400(client, auth_headers, sample_job):
    headers, _ = auth_headers
    csv_content = (
        "name,email,resume_text\n"
        ",bad1@example.com,No name here\n"
        "No resume,bad2@example.com,\n"
    )
    files = {"file": ("bad.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 400
    err = response.json()
    assert "No valid candidate rows" in err["detail"]["message"]
    assert len(err["detail"]["rejections"]) == 2


def test_binary_file_rejected_400(client, auth_headers, sample_job):
    headers, _ = auth_headers
    binary_content = b"name,email\x00\x01\x02\nSome binary content"
    files = {"file": ("binary.csv", io.BytesIO(binary_content), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 400
    assert "Binary file content is not allowed" in response.json()["detail"]


def test_non_utf8_rejected_400(client, auth_headers, sample_job):
    headers, _ = auth_headers
    # Invalid UTF-8 byte sequence
    bad_bytes = b"name,resume_text\nTest,\xff\xfe\xfaInvalid utf8"
    files = {"file": ("bad_utf8.csv", io.BytesIO(bad_bytes), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 400
    assert "not valid UTF-8" in response.json()["detail"]


def test_file_size_limit_413(client, auth_headers, sample_job, monkeypatch):
    headers, _ = auth_headers
    from app import config

    # Temporarily set max upload size to 100 bytes for test
    mock_settings = config.Settings(
        database_url="sqlite:///:memory:",
        jwt_secret="a" * 32,
        max_upload_size_bytes=100,
    )
    monkeypatch.setattr(config, "get_settings", lambda: mock_settings)
    from app.services import csv_ingest

    monkeypatch.setattr(csv_ingest, "get_settings", lambda: mock_settings)

    large_content = "name,resume_text\n" + ("A" * 200)
    files = {"file": ("large.csv", io.BytesIO(large_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 413
    assert "File exceeds maximum upload size" in response.json()["detail"]


def test_resume_length_limit(client, auth_headers, sample_job):
    headers, _ = auth_headers
    too_long_resume = "X" * 20001
    csv_content = f"name,resume_text\nToo Long,{too_long_resume}\n"
    files = {"file": ("long.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 400
    data = response.json()
    assert "exceeds maximum allowed length" in data["detail"]["rejections"][0]["reason"]


def test_upload_rejected_when_not_draft_or_done(client, auth_headers, sample_job, test_db):
    headers, _ = auth_headers
    sample_job.status = "failed"
    test_db.commit()

    csv_content = "name,resume_text\nValid,Developer with Python\n"
    files = {"file": ("c.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    assert response.status_code == 400
    assert "draft or done status" in response.json()["detail"]


def test_upload_isolated_to_job_owner(client, test_db, sample_job):
    # Create another user and attempt to upload to sample_job
    other_user = User(
        email="other@example.com",
        password_hash=hash_password("Password123!"),
    )
    test_db.add(other_user)
    test_db.commit()

    login_res = client.post(
        "/auth/login",
        json={"email": "other@example.com", "password": "Password123!"},
    )
    other_token = login_res.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    csv_content = "name,resume_text\nCandidate,Experience\n"
    files = {"file": ("c.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/jobs/{sample_job.id}/candidates", headers=other_headers, files=files)

    # Must be 404, not 403
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_upload_replace_false_returns_409_and_replace_true_overwrites(client, auth_headers, sample_job, test_db):
    headers, _ = auth_headers
    csv1 = "name,resume_text\nFirst Candidate,Python experience\n"
    files1 = {"file": ("c1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")}
    r1 = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files1)
    assert r1.status_code == 200
    assert r1.json()["rows_accepted"] == 1

    # Upload again with replace=false (default): 409 Conflict
    csv2 = "name,resume_text\nSecond Candidate,Go experience\n"
    files2 = {"file": ("c2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    r2 = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files2)
    assert r2.status_code == 409
    assert "already exist" in r2.json()["detail"]

    # Upload again with replace=true: overwrites and succeeds
    files3 = {"file": ("c3.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    r3 = client.post(f"/jobs/{sample_job.id}/candidates?replace=true", headers=headers, files=files3)
    assert r3.status_code == 200
    assert r3.json()["rows_accepted"] == 1

    # Verify only Second Candidate is now in DB
    cands = test_db.execute(select(Candidate).where(Candidate.job_id == sample_job.id)).scalars().all()
    assert len(cands) == 1
    assert cands[0].name == "Second Candidate"


def test_delete_candidates_endpoint(client, auth_headers, sample_job, test_db):
    headers, _ = auth_headers
    # Add candidate
    csv_data = "name,resume_text\nTo Delete,Some text\n"
    files = {"file": ("c.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)

    # Delete candidates
    del_res = client.delete(f"/jobs/{sample_job.id}/candidates", headers=headers)
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["detail"]

    # Verify empty in DB
    cands = test_db.execute(select(Candidate).where(Candidate.job_id == sample_job.id)).scalars().all()
    assert len(cands) == 0


def test_candidate_actions_while_processing_return_409(client, auth_headers, sample_job, test_db):
    headers, _ = auth_headers
    sample_job.status = "processing"
    test_db.commit()

    # Upload when processing -> 409
    csv_data = "name,resume_text\nTest,Some text\n"
    files = {"file": ("c.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    res_upload = client.post(f"/jobs/{sample_job.id}/candidates", headers=headers, files=files)
    assert res_upload.status_code == 409
    assert "processing" in res_upload.json()["detail"]

    # Delete when processing -> 409
    res_delete = client.delete(f"/jobs/{sample_job.id}/candidates", headers=headers)
    assert res_delete.status_code == 409
    assert "processing" in res_delete.json()["detail"]


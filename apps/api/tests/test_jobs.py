"""
Tests for jobs CRUD, scoping by owner_id, status constraints, and pagination
"""

import uuid
from sqlalchemy import select

from app.models import Job


def create_user_and_token(client, email="user@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_job_crud_happy_path(client):
    headers = create_user_and_token(client, "alice@example.com")

    # 1. Create job
    create_payload = {
        "title": "Senior Backend Engineer",
        "description": "We are seeking an experienced Python and FastAPI backend engineer to build scalable services.",
    }
    create_res = client.post("/jobs", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    job_data = create_res.json()
    job_id = job_data["id"]
    assert job_data["title"] == create_payload["title"]
    assert job_data["description"] == create_payload["description"]
    assert job_data["status"] == "draft"

    # 2. List jobs
    list_res = client.get("/jobs", headers=headers)
    assert list_res.status_code == 200
    jobs = list_res.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == job_id

    # 3. Get job by ID
    get_res = client.get(f"/jobs/{job_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job_id

    # 4. Patch job (draft status)
    patch_payload = {
        "title": "Staff Backend Engineer",
        "description": "Updated description with more than thirty characters required by validation.",
    }
    patch_res = client.patch(f"/jobs/{job_id}", json=patch_payload, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Staff Backend Engineer"

    # 5. Delete job
    delete_res = client.delete(f"/jobs/{job_id}", headers=headers)
    assert delete_res.status_code == 200

    # 6. Verify deleted
    get_after_delete = client.get(f"/jobs/{job_id}", headers=headers)
    assert get_after_delete.status_code == 404


def test_job_owner_isolation_404_not_403(client):
    headers_a = create_user_and_token(client, "alice@example.com")
    headers_b = create_user_and_token(client, "bob@example.com")

    # Alice creates a job
    create_res = client.post(
        "/jobs",
        json={
            "title": "Alice's Secret Job",
            "description": "Job description that belongs strictly to Alice and not Bob.",
        },
        headers=headers_a,
    )
    job_id = create_res.json()["id"]

    # Bob cannot read Alice's job -> 404 (never 403)
    get_res = client.get(f"/jobs/{job_id}", headers=headers_b)
    assert get_res.status_code == 404
    assert get_res.json()["detail"] == "Job not found"

    # Bob cannot update Alice's job -> 404 (never 403)
    patch_res = client.patch(
        f"/jobs/{job_id}",
        json={"title": "Bob Hijack Attempt"},
        headers=headers_b,
    )
    assert patch_res.status_code == 404
    assert patch_res.json()["detail"] == "Job not found"

    # Bob cannot delete Alice's job -> 404 (never 403)
    delete_res = client.delete(f"/jobs/{job_id}", headers=headers_b)
    assert delete_res.status_code == 404
    assert delete_res.json()["detail"] == "Job not found"

    # Alice's job is not visible in Bob's list
    bob_list = client.get("/jobs", headers=headers_b).json()
    assert len(bob_list) == 0


def test_nonexistent_job_returns_404(client):
    headers = create_user_and_token(client, "user@example.com")
    fake_id = str(uuid.uuid4())
    res = client.get(f"/jobs/{fake_id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Job not found"


def test_patch_rejected_when_not_draft(client, db_session):
    headers = create_user_and_token(client, "owner@example.com")
    create_res = client.post(
        "/jobs",
        json={
            "title": "Draft Job",
            "description": "A description with enough characters to pass validation checks.",
        },
        headers=headers,
    )
    job_id = uuid.UUID(create_res.json()["id"])

    # Simulate transition from draft to processing directly in DB
    job = db_session.execute(select(Job).where(Job.id == job_id)).scalar_one()
    job.status = "processing"
    db_session.commit()

    # Attempt to patch
    patch_res = client.patch(
        f"/jobs/{job_id}",
        json={"title": "New Title Attempt"},
        headers=headers,
    )
    assert patch_res.status_code == 400
    assert "Cannot edit a job that is not in draft status" in patch_res.json()["detail"]


def test_jobs_pagination(client):
    headers = create_user_and_token(client, "paginator@example.com")

    # Create 5 jobs
    import time
    for i in range(5):
        time.sleep(0.01)
        client.post(
            "/jobs",
            json={
                "title": f"Job Number {i}",
                "description": f"Valid job description with enough characters for job {i}.",
            },
            headers=headers,
        )

    # Limit = 2, offset = 0
    p1 = client.get("/jobs?limit=2&offset=0", headers=headers).json()
    assert len(p1) == 2
    assert p1[0]["title"] == "Job Number 4"
    assert p1[1]["title"] == "Job Number 3"

    # Limit = 2, offset = 2
    p2 = client.get("/jobs?limit=2&offset=2", headers=headers).json()
    assert len(p2) == 2
    assert p2[0]["title"] == "Job Number 2"
    assert p2[1]["title"] == "Job Number 1"

    # Limit = 2, offset = 4
    p3 = client.get("/jobs?limit=2&offset=4", headers=headers).json()
    assert len(p3) == 1
    assert p3[0]["title"] == "Job Number 0"


def test_job_validation_rules(client):
    headers = create_user_and_token(client, "validator@example.com")

    # Description too short (< 30 chars)
    res_short = client.post(
        "/jobs",
        json={"title": "Engineer", "description": "Too short"},
        headers=headers,
    )
    assert res_short.status_code == 422

    # Title empty
    res_empty_title = client.post(
        "/jobs",
        json={"title": "   ", "description": "Valid job description with enough characters to pass validation checks."},
        headers=headers,
    )
    assert res_empty_title.status_code == 422


def test_unauthenticated_requests_to_jobs_rejected(client):
    assert client.get("/jobs").status_code == 401
    assert client.post("/jobs", json={}).status_code == 401
    assert client.get(f"/jobs/{uuid.uuid4()}").status_code == 401
    assert client.patch(f"/jobs/{uuid.uuid4()}", json={}).status_code == 401
    assert client.delete(f"/jobs/{uuid.uuid4()}").status_code == 401

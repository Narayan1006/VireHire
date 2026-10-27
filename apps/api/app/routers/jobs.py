"""
Job management routes: /jobs
All endpoints require authentication and are strictly scoped by owner_id in code.
"""

from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Job, User, utc_now
from app.schemas import JobCreateRequest, JobResponse, JobUpdateRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new job in draft status owned by the authenticated user."""
    job = Job(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        status="draft",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=List[JobResponse])
def list_jobs(
    limit: int = Query(default=20, ge=1, le=100, description="Max jobs to return (max 100)"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns jobs owned by the current user ordered by newest first.
    Supports limit and offset pagination.
    """
    query = (
        select(Job)
        .where(Job.owner_id == current_user.id)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = db.execute(query).scalars().all()
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves a specific job owned by the current user.
    Returns 404 if the job does not exist or belongs to another user.
    """
    query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    job = db.execute(query).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates job title and/or description.
    Only permitted while the job status is 'draft'.
    Returns 404 if the job does not exist or belongs to another user.
    """
    query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    job = db.execute(query).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit a job that is not in draft status",
        )

    updated = False
    if payload.title is not None:
        job.title = payload.title
        updated = True
    if payload.description is not None:
        job.description = payload.description
        updated = True

    if updated:
        job.updated_at = utc_now()
        db.commit()
        db.refresh(job)

    return job


@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deletes a job owned by the current user.
    Returns 404 if the job does not exist or belongs to another user.
    """
    query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    job = db.execute(query).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    db.delete(job)
    db.commit()
    return {"detail": "Job deleted successfully"}

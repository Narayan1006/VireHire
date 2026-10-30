"""
Job management routes: /jobs
All endpoints require authentication and are strictly scoped by owner_id in code.
"""

from typing import List
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Candidate, Evidence, Job, Ranking, User, utc_now
from app.schemas import (
    CandidateEvidenceRow,
    CandidateResponse,
    EvidenceItem,
    IngestionReport,
    JobCreateRequest,
    JobEvidenceResponse,
    JobResponse,
    JobResultRow,
    JobResultsResponse,
    JobRunResponse,
    JobScoreResponse,
    JobUpdateRequest,
)
from app.services.csv_ingest import ingest_candidates_csv
from app.services.scoring import score_job
from app.services.tasks import (
    heavy_task_manager,
    run_evidence_collection_task,
    run_job_retrieval_task,
)

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


@router.post(
    "/{job_id}/candidates",
    response_model=IngestionReport,
    status_code=status.HTTP_200_OK,
)
async def upload_job_candidates(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    replace: bool = Query(default=False, description="Replace existing candidates and rankings if true"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads and parses a CSV of candidates for a job.
    Job must belong to authenticated user and be in draft or done status.
    Returns 409 if candidates already exist and replace=false.
    Returns 409 if job is currently processing.
    """
    with heavy_task_manager.acquire_for_background() as hand_off:
        query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
        job = db.execute(query).scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )

        if job.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job is currently processing",
            )

        if job.status not in ("draft", "done"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidates can only be uploaded when job is in draft or done status",
            )

        initial_status = job.status
        try:
            # Check for existing candidates
            existing_count = db.execute(
                select(sa.func.count(Candidate.id)).where(Candidate.job_id == job.id)
            ).scalar() or 0

            if existing_count > 0:
                if not replace:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Candidates already exist for this job. Use replace=true to overwrite.",
                    )
                # replace=True: delete existing rankings and candidates first
                db.execute(sa.delete(Ranking).where(Ranking.job_id == job.id))
                db.execute(sa.delete(Candidate).where(Candidate.job_id == job.id))
                db.commit()

            report = await ingest_candidates_csv(
                file=file,
                job=job,
                db=db,
                background_tasks=background_tasks,
            )
            hand_off()
            return report
        except Exception:
            db.rollback()
            try:
                job.status = initial_status
                db.commit()
            except Exception:
                pass
            raise


@router.delete(
    "/{job_id}/candidates",
    status_code=status.HTTP_200_OK,
)
def delete_job_candidates(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deletes all candidates and rankings for a job owned by the current user.
    Returns 409 if job is currently processing.
    """
    query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    job = db.execute(query).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete candidates while job is processing",
        )

    db.execute(sa.delete(Ranking).where(Ranking.job_id == job.id))
    db.execute(sa.delete(Candidate).where(Candidate.job_id == job.id))
    if job.status == "done":
        job.status = "draft"
    db.commit()
    return {"detail": "Candidates deleted successfully"}


@router.get(
    "/{job_id}/candidates",
    response_model=List[CandidateResponse],
)
def list_job_candidates(
    job_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists candidates for a job owned by the current user."""
    query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    job = db.execute(query).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    candidates_query = (
        select(Candidate)
        .where(Candidate.job_id == job_id)
        .order_by(Candidate.created_at.asc(), Candidate.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return db.execute(candidates_query).scalars().all()


@router.post(
    "/{job_id}/run",
    response_model=JobRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers hybrid retrieval for a job in the background.
    Returns 202 Accepted.
    Returns 409 if already processing or if no candidates are present.
    """
    with heavy_task_manager.acquire_for_background() as hand_off:
        settings = get_settings()
        query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
        job = db.execute(query).scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )

        if job.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job is already processing",
            )

        candidate_count = db.execute(
            select(sa.func.count(Candidate.id)).where(Candidate.job_id == job.id)
        ).scalar() or 0

        if candidate_count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No candidates found for this job",
            )

        initial_status = job.status
        try:
            job.status = "processing"
            job.error = None
            db.commit()

            background_tasks.add_task(run_job_retrieval_task, job.id, settings.retrieval_top_k)
            hand_off()
            return JobRunResponse(detail="Job run started", status="processing")
        except Exception:
            db.rollback()
            try:
                job.status = initial_status
                db.commit()
            except Exception:
                pass
            raise


@router.get(
    "/{job_id}/results",
    response_model=JobResultsResponse,
)
def get_job_results(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves ranked results for a job owned by the current user.
    Returns status, candidate count, and rows with 240-char snippet, retrieval_score,
    evidence_score, confidence, final_score, label, and breakdown reasons.
    Sorts by final_score descending when scored, else by retrieval rank, with stable tie-break.
    Never returns embeddings, tokens, emails, or raw payloads.
    """
    query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    job = db.execute(query).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    total_candidates = db.execute(
        select(sa.func.count(Candidate.id)).where(Candidate.job_id == job.id)
    ).scalar() or 0

    results_query = (
        select(Ranking, Candidate.name, Candidate.resume_text)
        .join(Candidate, Ranking.candidate_id == Candidate.id)
        .where(Ranking.job_id == job.id)
    )
    rows_data = list(db.execute(results_query).all())

    # Sort by final_score descending when scored, else by retrieval rank, with stable tie-break
    has_final_scores = any(r.final_score is not None for r, _, _ in rows_data)
    if has_final_scores:
        def sort_key(item):
            r = item[0]
            fs = r.final_score if r.final_score is not None else -1.0
            rs = r.retrieval_score if r.retrieval_score is not None else -1.0
            return (-fs, -rs, r.rank, str(r.candidate_id))

        rows_data.sort(key=sort_key)
    else:
        rows_data.sort(key=lambda item: (item[0].rank, str(item[0].candidate_id)))

    result_rows = [
        JobResultRow(
            rank=idx + 1,
            candidate_id=r.candidate_id,
            name=name,
            retrieval_score=r.retrieval_score,
            evidence_score=r.evidence_score,
            confidence=r.confidence,
            final_score=r.final_score,
            label=r.label,
            snippet=resume[:240].strip(),
            reasons=(r.breakdown or {}).get("reasons", []),
            breakdown=r.breakdown or {},
        )
        for idx, (r, name, resume) in enumerate(rows_data)
    ]

    return JobResultsResponse(
        status=job.status,
        candidate_count=total_candidates,
        rows=result_rows,
    )


@router.post(
    "/{job_id}/score",
    response_model=JobScoreResponse,
    status_code=status.HTTP_200_OK,
)
def score_job_endpoint(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Recomputes candidate scores, confidence, and labels from stored evidence
    WITHOUT making any external network calls.
    Owner-scoped: returns 404 for other users' jobs.
    Returns 409 if job is processing or if the job has no rankings.
    """
    query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    job = db.execute(query).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is currently processing",
        )

    ranking_count = db.execute(
        select(sa.func.count(Ranking.id)).where(Ranking.job_id == job.id)
    ).scalar() or 0

    if ranking_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job has no rankings. Run retrieval first.",
        )

    scored_count = score_job(job.id, db)
    return JobScoreResponse(detail="Scoring completed", candidates_scored=scored_count)


@router.post(
    "/{job_id}/verify",
    response_model=JobRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def verify_job_evidence(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers evidence collection for the top candidates of a job in the background.
    Owner-scoped: returns 404 for other users' jobs.
    Returns 409 if already processing or if the job has no rankings.
    Returns 202 Accepted otherwise.
    """
    with heavy_task_manager.acquire_for_background() as hand_off:
        query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
        job = db.execute(query).scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )

        if job.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job is already processing",
            )

        ranking_count = db.execute(
            select(sa.func.count(Ranking.id)).where(Ranking.job_id == job.id)
        ).scalar() or 0

        if ranking_count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job has no rankings. Run retrieval first.",
            )

        initial_status = job.status
        try:
            job.status = "processing"
            job.error = None
            db.commit()

            background_tasks.add_task(run_evidence_collection_task, job.id)
            hand_off()
            return JobRunResponse(detail="Evidence collection started", status="processing")
        except Exception:
            db.rollback()
            try:
                job.status = initial_status
                db.commit()
            except Exception:
                pass
            raise


@router.get(
    "/{job_id}/evidence",
    response_model=JobEvidenceResponse,
)
def get_job_evidence(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves collected evidence per ranked candidate for a job owned by the current user.
    Owner-scoped: returns 404 for other users' jobs.
    Returns source, username, status, reason, fetched_at, and compact payload.
    Never returns secrets, tokens, or emails.
    """
    query = select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    job = db.execute(query).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    rankings_query = (
        select(Ranking, Candidate.name)
        .join(Candidate, Ranking.candidate_id == Candidate.id)
        .where(Ranking.job_id == job.id)
        .order_by(Ranking.rank.asc())
    )
    ranked_candidates = db.execute(rankings_query).all()

    candidate_ids = [r.candidate_id for r, _ in ranked_candidates]
    evidence_map: dict[uuid.UUID, list[EvidenceItem]] = {cid: [] for cid in candidate_ids}

    if candidate_ids:
        ev_query = (
            select(Evidence)
            .where(Evidence.candidate_id.in_(candidate_ids))
            .order_by(Evidence.fetched_at.desc())
        )
        evidence_rows = db.execute(ev_query).scalars().all()
        for ev in evidence_rows:
            evidence_map[ev.candidate_id].append(
                EvidenceItem(
                    source=ev.source,
                    username=ev.username,
                    status=ev.status,
                    reason=ev.reason,
                    fetched_at=ev.fetched_at,
                    payload=ev.payload or {},
                )
            )

    rows = [
        CandidateEvidenceRow(
            rank=r.rank,
            candidate_id=r.candidate_id,
            name=name,
            evidence=evidence_map.get(r.candidate_id, []),
        )
        for r, name in ranked_candidates
    ]

    return JobEvidenceResponse(
        status=job.status,
        candidate_count=len(rows),
        rows=rows,
        candidates=rows,
    )



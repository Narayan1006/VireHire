"""
VeriHire v2 - Background Tasks for Candidate Embedding & Retrieval
Runs with independent database sessions; handles status transitions,
process-wide concurrency locking with leak-proof ownership hand-off,
stale job recovery, and generic error logging.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
import threading
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from app.database import get_session_factory
from app.models import Candidate, Job
from app.services.embedding import compute_embeddings
from app.services.retrieval import hybrid_retrieval, save_rankings

logger = logging.getLogger(__name__)



class HeavyTaskLockManager:
    """
    Manages process-wide execution serialization so only one candidate-embedding
    or retrieval task runs at a time. Provides a context manager that safely hands
    off lock ownership to a background task only upon successful request completion.
    """

    def __init__(self):
        self._lock = threading.Lock()

    @property
    def lock(self) -> threading.Lock:
        return self._lock

    def is_locked(self) -> bool:
        return self._lock.locked()

    def release_safe(self) -> None:
        """Safely release the lock without raising RuntimeError if already unlocked."""
        if self._lock.locked():
            try:
                self._lock.release()
            except RuntimeError:
                pass

    @contextmanager
    def acquire_for_background(self):
        """
        Acquires the lock for an endpoint that intends to delegate ownership
        to a background task upon successful completion of the request.

        If any error occurs within the context (validation, DB failure, scheduling error),
        the lock is immediately released.

        Only when `hand_off()` is explicitly called does the context manager NOT release
        the lock on exit, leaving release responsibility to the background task.
        """
        if not self._lock.acquire(blocking=False):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another job is running, try again shortly",
            )

        handed_off = False

        def hand_off():
            nonlocal handed_off
            handed_off = True

        try:
            yield hand_off
        finally:
            if not handed_off:
                self.release_safe()


heavy_task_manager = HeavyTaskLockManager()
# Backward-compatibility alias
heavy_task_lock = heavy_task_manager.lock


def recover_stale_jobs(db_factory=None) -> int:
    """
    On app startup, sets jobs with status 'processing' and updated_at older
    than 10 minutes to 'failed' with error "Interrupted, please retry".
    Returns the count of recovered jobs.
    """
    factory = db_factory or get_session_factory()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    with factory() as db:
        stale_jobs = db.execute(
            select(Job).where(Job.status == "processing")
        ).scalars().all()
        recovered = 0
        for job in stale_jobs:
            updated = job.updated_at
            if updated is not None:
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                if updated <= cutoff:
                    job.status = "failed"
                    job.error = "Interrupted, please retry"
                    recovered += 1
            else:
                job.status = "failed"
                job.error = "Interrupted, please retry"
                recovered += 1

        if recovered > 0:
            db.commit()
        return recovered


def embed_job_candidates_task(job_id: uuid.UUID, batch_size: int = 16) -> None:
    """
    Background task to compute embeddings for candidates of a job in batches of 16.
    Transitions: draft -> processing -> draft.
    On failure: sets status to 'failed' with a generic error message.
    Releases heavy_task_lock exactly once upon completion without error.
    """
    try:
        session_factory = get_session_factory()
        with session_factory() as db:
            try:
                job = db.get(Job, job_id)
                if not job:
                    return

                job.status = "processing"
                job.error = None
                db.commit()

                # Find candidates that do not yet have embeddings
                all_cands = db.execute(select(Candidate).where(Candidate.job_id == job_id)).scalars().all()
                unembedded = [c for c in all_cands if c.embedding is None or len(c.embedding) == 0]

                for i in range(0, len(unembedded), batch_size):
                    batch = unembedded[i : i + batch_size]
                    texts = [f"{c.name}\n{c.resume_text}" for c in batch]
                    embeddings = compute_embeddings(texts, batch_size=batch_size)
                    for c, emb in zip(batch, embeddings):
                        c.embedding = emb
                    db.commit()

                # Completed successfully -> return to draft status
                job = db.get(Job, job_id)
                if job:
                    job.status = "draft"
                    job.error = None
                    db.commit()

            except Exception:
                logger.exception("Failed to process candidate embeddings for job_id=%s", job_id)
                db.rollback()
                try:
                    job = db.get(Job, job_id)
                    if job:
                        job.status = "failed"
                        job.error = "Failed to process candidate embeddings"
                        db.commit()
                except Exception:
                    logger.exception("Failed to update status to failed for job_id=%s", job_id)
    except Exception:
        logger.exception("Unexpected error in embed_job_candidates_task for job_id=%s", job_id)
    finally:
        heavy_task_manager.release_safe()



def run_job_retrieval_task(job_id: uuid.UUID, top_k: int = 200) -> None:
    """
    Background task to run hybrid retrieval for a job.
    Transitions: processing -> done (or failed).
    Replaces rankings rows for this job.
    Releases heavy_task_lock exactly once upon completion without error.
    """
    try:
        session_factory = get_session_factory()
        with session_factory() as db:
            try:
                job = db.get(Job, job_id)
                if not job:
                    return

                job.status = "processing"
                job.error = None
                db.commit()

                # Ensure all candidates are embedded before running retrieval (batch size 16)
                all_cands = db.execute(select(Candidate).where(Candidate.job_id == job_id)).scalars().all()
                unembedded = [c for c in all_cands if c.embedding is None or len(c.embedding) == 0]
                if unembedded:
                    for i in range(0, len(unembedded), 16):
                        batch = unembedded[i : i + 16]
                        texts = [f"{c.name}\n{c.resume_text}" for c in batch]
                        embeddings = compute_embeddings(texts, batch_size=16)
                        for c, emb in zip(batch, embeddings):
                            c.embedding = emb
                        db.commit()

                # Run hybrid retrieval
                scored_candidates = hybrid_retrieval(
                    job_id=job.id,
                    query_text=job.description,
                    db=db,
                    top_k=top_k,
                )

                # Persist rankings
                save_rankings(job_id=job.id, scored_candidates=scored_candidates, db=db)

                job = db.get(Job, job_id)
                if job:
                    job.status = "done"
                    job.error = None
                    db.commit()

            except Exception:
                logger.exception("Failed to run candidate retrieval for job_id=%s", job_id)
                db.rollback()
                try:
                    job = db.get(Job, job_id)
                    if job:
                        job.status = "failed"
                        job.error = "Failed to run candidate retrieval"
                        db.commit()
                except Exception:
                    logger.exception("Failed to update status to failed for job_id=%s", job_id)
    except Exception:
        logger.exception("Unexpected error in run_job_retrieval_task for job_id=%s", job_id)
    finally:
        heavy_task_manager.release_safe()


def run_evidence_collection_task(job_id: uuid.UUID) -> None:
    """
    Background task to collect evidence for a job.
    Transitions: processing -> done (or failed).
    Releases heavy_task_lock exactly once upon completion without error.
    """
    try:
        session_factory = get_session_factory()
        with session_factory() as db:
            try:
                job = db.get(Job, job_id)
                if not job:
                    return

                job.status = "processing"
                job.error = None
                db.commit()

                from app.services.evidence import collect_evidence_for_job

                collect_evidence_for_job(job_id)

                job = db.get(Job, job_id)
                if job:
                    job.status = "done"
                    job.error = None
                    db.commit()

            except Exception:
                logger.exception("Failed to collect evidence for job_id=%s", job_id)
                db.rollback()
                try:
                    job = db.get(Job, job_id)
                    if job:
                        job.status = "failed"
                        job.error = "Failed to collect evidence"
                        db.commit()
                except Exception:
                    logger.exception("Failed to update status to failed for job_id=%s", job_id)
    except Exception:
        logger.exception("Unexpected error in run_evidence_collection_task for job_id=%s", job_id)
    finally:
        heavy_task_manager.release_safe()


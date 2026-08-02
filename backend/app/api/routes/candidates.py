"""
VeriHire AI - Candidates API Endpoints

GET /api/candidates: List ranked candidates with filtering/pagination.
GET /api/candidates/{candidate_id}: Get single candidate detail.

Requirements: 18.1-18.5, 19.1-19.5
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.api_schemas import CandidatesResponse, ErrorResponse
from app.models.candidate import CandidateOutput
from app.storage import get_store
from app.utils.auth import get_current_user
from app.utils.cache import get_cache, CacheManager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Candidates"])

_store = get_store()


@router.get(
    "/candidates",
    response_model=CandidatesResponse,
    summary="List ranked candidates",
    description="Retrieve ranked candidates with optional filtering and pagination.",
)
def list_candidates(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    verdict: Optional[str] = Query(None, description="Filter by verdict: HIRE, REVIEW, REJECT"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum PR score"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(get_current_user),
):
    """List candidates with filtering and pagination."""
    # Determine job_id
    target_job = job_id or _store.get_latest_job_id()
    if not target_job:
        return CandidatesResponse(total=0, limit=limit, offset=offset, candidates=[])

    # Try cache first
    cache = get_cache()
    cache_key = CacheManager.ranking_key(target_job)
    candidates = cache.get(cache_key)

    if candidates is None:
        # Load from store
        candidates = _store.load_candidates(target_job)
        if candidates is None:
            return CandidatesResponse(total=0, limit=limit, offset=offset, candidates=[])
        # Warm cache
        cache.set(cache_key, candidates)

    # Apply filters
    filtered = candidates
    if verdict:
        filtered = [c for c in filtered if c.verdict == verdict.upper()]
    if min_score is not None:
        filtered = [c for c in filtered if c.pr_score >= min_score]

    # Paginate
    total = len(filtered)
    page = filtered[offset : offset + limit]

    return CandidatesResponse(
        total=total,
        limit=limit,
        offset=offset,
        candidates=page,
    )


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateOutput,
    responses={404: {"model": ErrorResponse}},
    summary="Get candidate detail",
    description="Retrieve complete details for a single candidate.",
)
def get_candidate(
    candidate_id: str,
    job_id: Optional[str] = Query(None, description="Job ID (defaults to latest)"),
    current_user: dict = Depends(get_current_user),
):
    """Get a single candidate by ID."""
    target_job = job_id or _store.get_latest_job_id()
    if not target_job:
        raise HTTPException(status_code=404, detail="No ranking results found")

    candidate = _store.get_candidate(target_job, candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {candidate_id} not found",
        )

    return candidate

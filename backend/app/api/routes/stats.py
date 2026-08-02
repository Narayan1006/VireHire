"""
VeriHire AI - Statistics API Endpoint

GET /api/stats: Dashboard summary statistics.

Requirements: 21.1-21.5
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.models.api_schemas import DashboardStats
from app.storage import get_store
from app.utils.auth import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Statistics"])

_store = get_store()


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    description="Retrieve summary statistics for the latest or specified ranking job.",
)
def get_stats(
    job_id: Optional[str] = Query(None, description="Job ID (defaults to latest)"),
    current_user: dict = Depends(get_current_user),
):
    """Calculate and return dashboard statistics."""
    target_job = job_id or _store.get_latest_job_id()
    if not target_job:
        return DashboardStats(
            total_candidates=0,
            avg_score=0,
            verified_profiles=0,
        )

    candidates = _store.load_candidates(target_job)
    if not candidates:
        return DashboardStats(
            total_candidates=0,
            avg_score=0,
            verified_profiles=0,
        )

    total = len(candidates)

    # Average PR score
    avg_score = round(sum(c.pr_score for c in candidates) / total) if total else 0

    # Verified profiles (has at least one verified evidence source)
    verified = sum(
        1 for c in candidates
        if c.github_evidence.verified
        or c.leetcode.verified
        or (c.codeforces and c.codeforces.verified)
    )

    # Verdict breakdown
    breakdown = {"HIRE": 0, "REVIEW": 0, "REJECT": 0}
    scores_by_verdict = {"HIRE": [], "REVIEW": [], "REJECT": []}
    for c in candidates:
        breakdown[c.verdict] = breakdown.get(c.verdict, 0) + 1
        scores_by_verdict.setdefault(c.verdict, []).append(c.pr_score)

    # Average scores by verdict
    avg_by_verdict = {}
    for v, scores in scores_by_verdict.items():
        avg_by_verdict[v] = round(sum(scores) / len(scores)) if scores else 0

    # Time saved estimate: 15 min per candidate manual review
    hours_saved = round(total * 15 / 60, 1)

    return DashboardStats(
        total_candidates=total,
        avg_score=avg_score,
        verified_profiles=verified,
        time_saved=f"{hours_saved} hrs",
        verdict_breakdown=breakdown,
        avg_scores_by_verdict=avg_by_verdict,
    )

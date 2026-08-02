"""
VeriHire AI - API Request/Response Schemas

Pydantic models for all FastAPI endpoint contracts:
- RankRequest / RankResponse: POST /api/rank
- CandidatesResponse: GET /api/candidates
- DashboardStats: GET /api/stats
- HealthResponse: GET /api/health
- ErrorResponse: Standardized error format
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.candidate import CandidateOutput


# ── POST /api/rank ────────────────────────────────────────────────


class RankRequest(BaseModel):
    """Request body for the ranking pipeline trigger."""

    job_description: str = Field(
        min_length=50,
        max_length=5000,
        description="Job description text (50-5000 characters)",
    )
    csv_file_path: str = Field(
        description="Path to the Kaggle CSV data file",
    )
    top_k: int = Field(
        default=200,
        gt=0,
        description="Number of candidates to pass from Layer 1 to Layer 2",
    )
    llm_top_k: int = Field(
        default=50,
        gt=0,
        description="Number of candidates to pass from Layer 2 to Layer 3",
    )


class RankResponse(BaseModel):
    """Response for a ranking pipeline trigger."""

    job_id: str
    status: str = Field(description='Pipeline status: "processing", "completed", or "failed"')
    message: str = ""
    estimated_time_seconds: int = Field(default=180)


# ── POST /api/upload/csv ──────────────────────────────────────────


class UploadCsvResponse(BaseModel):
    """Response after a successful CSV upload."""

    file_path: str = Field(description="Server path to use in POST /api/rank")
    filename: str
    total_rows: int
    valid_candidates: int


# ── GET /api/candidates ──────────────────────────────────────────


class CandidatesResponse(BaseModel):
    """Paginated response of ranked candidates."""

    total: int = Field(ge=0, description="Total candidates matching filters")
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    candidates: List[CandidateOutput]


# ── GET /api/stats ────────────────────────────────────────────────


class DashboardStats(BaseModel):
    """Dashboard summary statistics."""

    total_candidates: int = Field(ge=0)
    avg_score: int = Field(ge=0, le=100)
    verified_profiles: int = Field(ge=0)
    time_saved: str = Field(default="0 hrs", description="Estimated recruiter time saved")
    verdict_breakdown: Dict[str, int] = Field(
        default_factory=lambda: {"HIRE": 0, "REVIEW": 0, "REJECT": 0},
        description="Count of candidates per verdict",
    )
    avg_scores_by_verdict: Dict[str, int] = Field(
        default_factory=lambda: {"HIRE": 0, "REVIEW": 0, "REJECT": 0},
        description="Average PR score per verdict",
    )


# ── GET /api/health ───────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description='System status: "healthy", "degraded", or "unhealthy"')
    version: str
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Service connectivity status",
    )


# ── Error Response ────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standardized error response for all API errors."""

    error: str = Field(description="Error type (e.g., ValidationError, NotFoundError)")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )

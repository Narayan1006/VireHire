"""
VeriHire AI - Export API Endpoint

GET /api/export: Export ranked candidates as CSV or JSON.

Requirements: 20.1-20.5, 29.1-29.5
"""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, JSONResponse

from app.storage import get_store
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Export"])

_store = get_store()


@router.get(
    "/export",
    summary="Export ranked candidates",
    description="Export candidates as CSV or JSON with optional filtering.",
)
def export_candidates(
    job_id: Optional[str] = Query(None, description="Job ID (defaults to latest)"),
    verdict: Optional[str] = Query(None, description="Filter by verdict"),
    format: str = Query("csv", description="Export format: csv or json"),
):
    """Export candidates in CSV or JSON format."""
    target_job = job_id or _store.get_latest_job_id()
    if not target_job:
        return JSONResponse(
            content={"error": "No ranking results found"},
            status_code=404,
        )

    candidates = _store.load_candidates(target_job)
    if not candidates:
        return JSONResponse(
            content={"error": "No candidates found for this job"},
            status_code=404,
        )

    # Apply verdict filter
    if verdict:
        candidates = [c for c in candidates if c.verdict == verdict.upper()]

    if format.lower() == "json":
        return _export_json(candidates, target_job)
    else:
        return _export_csv(candidates, target_job)


def _export_csv(candidates, job_id: str) -> StreamingResponse:
    """Generate CSV export with BOM for Excel compatibility."""
    output = io.StringIO()
    # UTF-8 BOM for Excel
    output.write("\ufeff")

    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Header
    writer.writerow([
        "Rank", "Name", "Email", "Role", "Percentile", "PR Score",
        "GitHub Score", "DSA Score", "Verdict", "Skills",
        "Risk Flags", "Summary",
    ])

    # Rows
    for c in candidates:
        skills = "; ".join(
            f"{s.name}:{s.verified}" for s in c.skills
        ) if c.skills else ""

        flags = "; ".join(
            f"{f.label} ({f.severity})" for f in c.risk_flags
        ) if c.risk_flags else ""

        summary = (c.summary or "")[:500]

        writer.writerow([
            c.rank, c.name, c.email, c.role, c.percentile, c.pr_score,
            c.github_score, c.dsa_score, c.verdict, skills, flags, summary,
        ])

    output.seek(0)
    filename = f"verihire_results_{job_id}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def _export_json(candidates, job_id: str) -> StreamingResponse:
    """Generate JSON export."""
    import json

    data = {
        "job_id": job_id,
        "total": len(candidates),
        "candidates": [c.model_dump(mode="json") for c in candidates],
    }

    content = json.dumps(data, indent=2, default=str)
    filename = f"verihire_results_{job_id}.json"

    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

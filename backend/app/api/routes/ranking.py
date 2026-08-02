"""
VeriHire AI - Ranking API Endpoint

POST /api/rank: Trigger the 3-layer ranking pipeline.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5
"""

import io
import uuid
import threading
from typing import Dict

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.models.api_schemas import RankResponse, ErrorResponse
from app.parsers.csv_parser import load_csv_bytes
from app.services.orchestrator import PipelineOrchestrator
from app.storage import get_store
from app.utils.auth import get_current_user
from app.utils.cache import get_cache, CacheManager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Ranking"])

# Track pipeline jobs
_pipeline_jobs: Dict[str, dict] = {}
_store = get_store()


@router.post(
    "/rank",
    response_model=RankResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Trigger candidate ranking pipeline",
    description="Submit a job description and CSV file to start the 3-layer AI ranking pipeline.",
)
async def trigger_ranking(
    job_description: str = Form(
        ...,
        min_length=50,
        max_length=5000,
        description="Job description text (50-5000 characters)",
    ),
    csv_file: UploadFile = File(..., description="Candidate CSV (parsed in memory)"),
    top_k: int = Form(200, gt=0),
    llm_top_k: int = Form(50, gt=0),
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger the ranking pipeline asynchronously.

    CSV is read into memory — nothing is written to disk (Render-safe).
    Returns 202 Accepted with a job_id for tracking.
    """
    content = await csv_file.read()
    try:
        candidates, _total_rows = load_csv_bytes(content)
        if not candidates:
            raise ValueError("No valid candidates found in CSV")
        df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "ValidationError", "message": str(e)},
        ) from e

    job_id = str(uuid.uuid4())[:8]
    user_id = current_user["id"]  # Extract user ID for database storage

    _pipeline_jobs[job_id] = {
        "status": "processing",
        "message": "Pipeline started",
    }

    thread = threading.Thread(
        target=_run_pipeline_async,
        args=(job_id, job_description, df, top_k, llm_top_k, user_id),
        daemon=True,
    )
    thread.start()

    logger.info("Pipeline triggered: job_id=%s, user_id=%s", job_id, user_id)

    return RankResponse(
        job_id=job_id,
        status="processing",
        message="Ranking pipeline started. Use GET /api/candidates?job_id={job_id} to retrieve results.",
        estimated_time_seconds=120,
    )


@router.get(
    "/rank/{job_id}/status",
    summary="Get pipeline job status",
)
def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Check the status of a pipeline job."""
    job = _pipeline_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _run_pipeline_async(
    job_id: str,
    job_description: str,
    df: pd.DataFrame,
    top_k: int,
    llm_top_k: int,
    user_id: str,
):
    """Execute the pipeline in a background thread."""
    try:
        settings = get_settings()
        pipeline = PipelineOrchestrator(settings)

        results = pipeline.execute_pipeline(
            job_description=job_description,
            df=df,
            layer1_top_k=top_k,
            layer2_top_k=llm_top_k,
        )

        _store.save_candidates(job_id, results, job_description, user_id=user_id)

        cache = get_cache()
        cache.set(CacheManager.ranking_key(job_id), results)

        _pipeline_jobs[job_id] = {
            "status": "completed",
            "message": f"Pipeline complete: {len(results)} candidates ranked",
            "total_candidates": len(results),
        }

        logger.info("Pipeline job %s completed: %d results", job_id, len(results))

    except Exception as e:
        logger.error("Pipeline job %s failed: %s", job_id, str(e))
        _pipeline_jobs[job_id] = {
            "status": "failed",
            "message": str(e),
        }

"""
VeriHire AI - Internal Pipeline API Endpoint

POST /pipeline/rank: Internal endpoint called ONLY by Spring Boot.

Receives job description + CSV bytes in-memory, executes 3-layer AI pipeline,
and returns structured JSON rankings (CandidateOutput[]).

NO authentication required on this internal service.
NO database writes — completely stateless.
"""

import io
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import pandas as pd

from app.models.candidate import CandidateOutput
from app.models.api_schemas import ErrorResponse
from app.parsers.csv_parser import MAX_CSV_SIZE_BYTES
from app.services.orchestrator import PipelineOrchestrator
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])
orchestrator = PipelineOrchestrator()


@router.post(
    "/rank",
    response_model=List[CandidateOutput],
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Execute 3-layer AI ranking pipeline",
    description="Internal endpoint called by Spring Boot. Receives job description and CSV file, runs AI pipeline, returns JSON rankings.",
)
async def run_pipeline(
    job_description: str = Form(..., description="Target Job Description text"),
    csv_file: UploadFile = File(..., description="Candidate dataset CSV file"),
    layer1_top_k: Optional[int] = Form(200, description="Layer 1 top K candidates"),
    layer2_top_k: Optional[int] = Form(50, description="Layer 2 top K candidates"),
    provider: Optional[str] = Form("groq", description="AI Provider (groq/ollama)"),
    github_token: Optional[str] = Form("", description="GitHub personal access token"),
    groq_api_key: Optional[str] = Form("", description="Groq API key"),
    ollama_base_url: Optional[str] = Form("http://localhost:11434", description="Ollama base URL"),
):
    """Execute AI pipeline and return CandidateOutput[] JSON."""
    if not job_description or not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Job description cannot be empty.",
            },
        )

    if not csv_file.filename or not csv_file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Only .csv files are accepted.",
            },
        )

    content = await csv_file.read()
    if len(content) > MAX_CSV_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "CSV file exceeds size limit (50MB).",
            },
        )

    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Uploaded CSV file is empty.",
            },
        )

    # Parse CSV in memory (no disk write)
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        logger.error("Failed to parse CSV bytes: %s", e)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": f"Invalid CSV format: {str(e)[:200]}",
            },
        ) from e

    logger.info(
        "Starting AI pipeline: rows=%d, jd_len=%d",
        len(df),
        len(job_description),
    )

    try:
        results = orchestrator.execute_pipeline(
            job_description=job_description,
            df=df,
            layer1_top_k=layer1_top_k,
            layer2_top_k=layer2_top_k,
            provider=provider,
            github_token=github_token,
            groq_api_key=groq_api_key,
            ollama_base_url=ollama_base_url,
        )
        logger.info("AI pipeline complete: returned %d ranked candidates", len(results))
        return results

    except Exception as e:
        logger.error("AI pipeline execution failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "PipelineError",
                "message": f"AI pipeline failed: {str(e)[:200]}",
            },
        ) from e

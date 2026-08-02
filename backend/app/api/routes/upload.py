"""
VeriHire AI - Dataset Upload API

POST /api/upload/csv: Upload a recruiter candidate CSV for ranking.
"""

import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.api_schemas import UploadCsvResponse, ErrorResponse
from app.parsers.csv_parser import load_csv, MAX_CSV_SIZE_BYTES
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Upload"])

UPLOAD_DIR = "data/uploads"


@router.post(
    "/upload/csv",
    response_model=UploadCsvResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Upload candidate CSV dataset",
    description="Upload a CSV file containing candidate records for ranking.",
)
async def upload_csv(file: UploadFile = File(...)):
    """Save an uploaded CSV and return the server path for ranking."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Only .csv files are accepted.",
            },
        )

    content = await file.read()
    if len(content) > MAX_CSV_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "CSV file exceeds 50 MB limit.",
            },
        )

    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Uploaded file is empty.",
            },
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())[:12]
    safe_name = os.path.basename(file.filename).replace(" ", "_")
    stored_name = f"{file_id}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        candidates, total_rows = load_csv(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": f"Invalid CSV: {str(e)[:200]}",
            },
        ) from e

    if not candidates:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": (
                    f"No valid candidate rows from {total_rows} rows. "
                    "Required column: role (or job_title, position, job_position_name). "
                    "Empty rows are skipped."
                ),
            },
        )

    logger.info(
        "CSV uploaded: path=%s rows=%d valid=%d",
        file_path,
        total_rows,
        len(candidates),
    )

    return UploadCsvResponse(
        file_path=file_path.replace("\\", "/"),
        filename=file.filename,
        total_rows=total_rows,
        valid_candidates=len(candidates),
    )

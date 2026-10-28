"""
VeriHire v2 - Candidate CSV Ingestion Service
Handles streaming reading, size limits, binary rejection, flexible header mapping,
URL normalization, row validation, embedding generation, and reporting.
"""

import csv
import io
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Candidate, Job
from app.schemas import IngestionReport, RejectionDetail
from app.security import validate_and_normalize_email
from app.services.tasks import embed_job_candidates_task

# Header aliases (normalized lowercase stripped)
HEADER_ALIASES = {
    "name": ["name", "full_name", "candidate_name"],
    "email": ["email", "email_address"],
    "summary": ["summary"],
    "skills": ["skills"],
    "experience": ["experience"],
    "resume": ["resume"],
    "resume_text": ["resume_text"],
    "github": ["github", "github_url", "github_link"],
    "leetcode": ["leetcode", "leetcode_url", "leetcode_link"],
    "linkedin": ["linkedin", "linkedin_url", "linkedin_link"],
}

STABLE_RESUME_TEXT_ORDER = ["summary", "skills", "experience", "resume", "resume_text"]

GITHUB_USER_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")
LEETCODE_USER_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,60}$")


def normalize_github_url(raw: str) -> Optional[str]:
    """Normalizes and validates a GitHub profile URL or username."""
    s = raw.strip()
    if not s:
        return None

    # Handle full or partial URL
    s = re.sub(r"^https?://", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^www\.", "", s, flags=re.IGNORECASE)

    if s.lower().startswith("github.com/"):
        s = s[len("github.com/") :]

    s = s.strip("/").lstrip("@")
    parts = s.split("/")
    username = parts[0].strip()

    if not username or not GITHUB_USER_REGEX.match(username):
        return None

    return f"https://github.com/{username}"


def normalize_leetcode_url(raw: str) -> Optional[str]:
    """Normalizes and validates a LeetCode profile URL or username."""
    s = raw.strip()
    if not s:
        return None

    s = re.sub(r"^https?://", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^www\.", "", s, flags=re.IGNORECASE)

    if s.lower().startswith("leetcode.com/"):
        s = s[len("leetcode.com/") :]

    s = s.strip("/").lstrip("@")
    parts = [p for p in s.split("/") if p]
    if not parts:
        return None

    # Leetcode uses /u/<username> or /<username>
    username = parts[1] if parts[0].lower() == "u" and len(parts) > 1 else parts[0]
    username = username.strip()

    if not username or not LEETCODE_USER_REGEX.match(username):
        return None

    return f"https://leetcode.com/u/{username}"


def normalize_linkedin_url(raw: str) -> Optional[str]:
    """Normalizes a LinkedIn profile URL or username."""
    s = raw.strip()
    if not s:
        return None

    s = re.sub(r"^https?://", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^www\.", "", s, flags=re.IGNORECASE)

    if s.lower().startswith("linkedin.com/"):
        s = s[len("linkedin.com/") :]

    s = s.strip("/").lstrip("@")
    parts = [p for p in s.split("/") if p]
    if not parts:
        return None

    slug = parts[1] if parts[0].lower() == "in" and len(parts) > 1 else parts[0]
    slug = slug.strip()
    if not slug:
        return None

    return f"https://www.linkedin.com/in/{slug}"


async def read_and_validate_file_content(file: UploadFile, max_bytes: int) -> str:
    """
    Reads the uploaded file in chunks while enforcing the size limit.
    Decodes utf-8-sig and rejects binary content.
    """
    chunks = []
    total_bytes = 0

    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum upload size of {max_bytes // (1024 * 1024)} MB",
            )
        chunks.append(chunk)

    raw_content = b"".join(chunks)
    if not raw_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Check for binary null bytes
    if b"\x00" in raw_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Binary file content is not allowed; must be a valid UTF-8 CSV",
        )

    try:
        text_content = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not valid UTF-8 text",
        )

    return text_content


def map_headers(fieldnames: List[str]) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Maps CSV header names to standard fields using aliases.
    Returns:
      field_to_columns: target field -> list of source CSV column headers
      matched_targets: list of targets identified
    """
    field_to_columns: Dict[str, List[str]] = {}
    normalized_to_source = {h.strip().lower(): h for h in fieldnames if h}

    for target, aliases in HEADER_ALIASES.items():
        matched = []
        for alias in aliases:
            if alias in normalized_to_source:
                matched.append(normalized_to_source[alias])
        if matched:
            field_to_columns[target] = matched

    return field_to_columns, list(field_to_columns.keys())


def parse_and_validate_csv(
    text_content: str,
    job_id: uuid.UUID,
    db: Session,
) -> Tuple[List[Dict[str, Any]], List[RejectionDetail]]:
    """
    Parses CSV, checks row count and row validity, and returns
    accepted rows and rejection details.
    """
    settings = get_settings()

    f = io.StringIO(text_content)
    try:
        reader = csv.DictReader(f)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(exc)}",
        )

    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains no headers",
        )

    field_map, matched_targets = map_headers(reader.fieldnames)

    # Must at least have a header that could provide name
    if "name" not in field_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV missing required 'name' or 'full_name' column",
        )

    # Fetch existing emails for this job to detect duplicates
    existing_emails_stmt = select(Candidate.email).where(
        Candidate.job_id == job_id,
        Candidate.email.isnot(None),
    )
    existing_emails = {
        e.lower() for (e,) in db.execute(existing_emails_stmt).fetchall() if e
    }

    seen_emails_in_upload: Set[str] = set()
    accepted_rows: List[Dict[str, Any]] = []
    rejections: List[RejectionDetail] = []

    row_count = 0
    # Header is row 1, first data row is row 2
    for row_idx, row in enumerate(reader, start=2):
        row_count += 1
        if row_count > settings.max_csv_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV exceeds maximum limit of {settings.max_csv_rows} rows",
            )

        # 1. Extract name
        name_val = ""
        for col in field_map.get("name", []):
            if row.get(col):
                name_val = row[col].strip()
                break

        if not name_val:
            rejections.append(RejectionDetail(row_number=row_idx, reason="missing name"))
            continue

        if len(name_val) > 200:
            name_val = name_val[:200]

        # 2. Extract resume text from all available text fields in stable order
        text_parts = []
        for target_field in STABLE_RESUME_TEXT_ORDER:
            for col in field_map.get(target_field, []):
                val = (row.get(col) or "").strip()
                if val:
                    text_parts.append(val)

        resume_text = "\n\n".join(text_parts).strip()
        if not resume_text:
            rejections.append(RejectionDetail(row_number=row_idx, reason="empty resume text"))
            continue

        if len(resume_text) > settings.max_resume_length:
            rejections.append(
                RejectionDetail(
                    row_number=row_idx,
                    reason=f"resume text exceeds maximum allowed length of {settings.max_resume_length} characters",
                )
            )
            continue

        # 3. Extract and validate email (optional, but validated if present)
        email_val: Optional[str] = None
        for col in field_map.get("email", []):
            if row.get(col) and row[col].strip():
                raw_email = row[col].strip()
                try:
                    email_val = validate_and_normalize_email(raw_email)
                except Exception:
                    email_val = "INVALID"
                break

        if email_val == "INVALID":
            rejections.append(RejectionDetail(row_number=row_idx, reason="invalid email"))
            continue

        if email_val:
            if email_val in seen_emails_in_upload:
                rejections.append(
                    RejectionDetail(row_number=row_idx, reason="duplicate email in upload")
                )
                continue
            if email_val in existing_emails:
                rejections.append(
                    RejectionDetail(row_number=row_idx, reason="duplicate email for this job")
                )
                continue
            seen_emails_in_upload.add(email_val)

        # 4. Extract links (GitHub, LeetCode, LinkedIn)
        links: Dict[str, str] = {}
        github_error = False
        for col in field_map.get("github", []):
            raw_gh = (row.get(col) or "").strip()
            if raw_gh:
                norm_gh = normalize_github_url(raw_gh)
                if not norm_gh:
                    github_error = True
                else:
                    links["github"] = norm_gh
                break

        if github_error:
            rejections.append(RejectionDetail(row_number=row_idx, reason="invalid github url"))
            continue

        leetcode_error = False
        for col in field_map.get("leetcode", []):
            raw_lc = (row.get(col) or "").strip()
            if raw_lc:
                norm_lc = normalize_leetcode_url(raw_lc)
                if not norm_lc:
                    leetcode_error = True
                else:
                    links["leetcode"] = norm_lc
                break

        if leetcode_error:
            rejections.append(RejectionDetail(row_number=row_idx, reason="invalid leetcode url"))
            continue

        for col in field_map.get("linkedin", []):
            raw_li = (row.get(col) or "").strip()
            if raw_li:
                norm_li = normalize_linkedin_url(raw_li)
                if norm_li:
                    links["linkedin"] = norm_li
                break

        accepted_rows.append(
            {
                "name": name_val,
                "email": email_val,
                "resume_text": resume_text,
                "links": links,
            }
        )

    return accepted_rows, rejections


async def ingest_candidates_csv(
    file: UploadFile,
    job: Job,
    db: Session,
    background_tasks: Optional[BackgroundTasks] = None,
) -> IngestionReport:
    """
    Coordinates file reading, CSV parsing/validation, database insertion,
    and enqueues background embedding computation.
    """
    settings = get_settings()

    text_content = await read_and_validate_file_content(
        file, max_bytes=settings.max_upload_size_bytes
    )

    accepted_rows, rejections = parse_and_validate_csv(
        text_content=text_content,
        job_id=job.id,
        db=db,
    )

    if not accepted_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "No valid candidate rows could be accepted from the CSV upload.",
                "rejections": [r.model_dump() for r in rejections],
            },
        )

    # Insert candidates initially with embedding = None
    new_candidates = []
    for row_data in accepted_rows:
        candidate = Candidate(
            job_id=job.id,
            name=row_data["name"],
            email=row_data["email"],
            resume_text=row_data["resume_text"],
            links=row_data["links"],
            embedding=None,
        )
        new_candidates.append(candidate)

    db.add_all(new_candidates)
    job.status = "processing"
    job.error = None
    db.commit()

    if background_tasks:
        background_tasks.add_task(embed_job_candidates_task, job.id, 16)
    else:
        embed_job_candidates_task(job.id, 16)

    return IngestionReport(
        rows_accepted=len(new_candidates),
        rows_rejected=rejections,
    )


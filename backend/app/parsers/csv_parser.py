"""
VeriHire AI - CSV Parser

Loads candidate records from a Kaggle CSV file and returns a list of
CandidateInput objects.  Validates required fields, logs warnings for
invalid records, and supports files up to 50 MB.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 23.4
"""

import io
import os
import re
import uuid
from typing import List, Tuple

import pandas as pd

from app.models.candidate import CandidateInput
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Maximum CSV file size: 50 MB
MAX_CSV_SIZE_BYTES = 50 * 1024 * 1024

# Columns required for a valid candidate record (relaxed for Kaggle datasets)
REQUIRED_COLUMNS = {"role"}

# Email validation regex (simplified standard pattern)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Common ATS / export column names → our schema
COLUMN_ALIASES = {
    "job_title": "role",
    "job_position": "role",
    "job_position_name": "role",
    "position": "role",
    "title": "role",
    "job_role": "role",
    "candidate_name": "name",
    "full_name": "name",
    "applicant_name": "name",
    "email_address": "email",
    "e_mail": "email",
    "career_objective": "_career_objective",
}

# Kaggle column → our column mapping (legacy names)
KAGGLE_COLUMN_MAP = {
    "job_position_name": "role",
    "career_objective": "_career_objective",
}


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, strip BOM, spaces → underscores, apply aliases."""
    df = df.copy()
    df.columns = [
        str(col).strip().lower().replace(" ", "_").lstrip("\ufeff")
        for col in df.columns
    ]
    rename = {col: COLUMN_ALIASES[col] for col in df.columns if col in COLUMN_ALIASES}
    if rename:
        df = df.rename(columns=rename)
        logger.info("Applied column aliases: %s", rename)
    return df


def _apply_column_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map Kaggle dataset columns to our expected schema.

    Handles two CSV formats:
      1. Our format: id, name, email, role, skills, ...
      2. Kaggle format: job_position_name, career_objective, skills, ...

    For Kaggle format, auto-generates id, name, and email fields.
    """
    cols = set(df.columns)

    # Derive role from career objective if still missing
    if "role" not in cols and "_career_objective" in cols:
        df["role"] = df["_career_objective"].apply(
            lambda v: (_clean_string(v)[:80] or "Applicant")
        )

    # If our required columns exist, no mapping needed
    if "role" in cols:
        # Ensure name/email exist with defaults
        if "name" not in cols:
            df["name"] = [f"Candidate_{i+1}" for i in range(len(df))]
        if "email" not in cols:
            df["email"] = [f"candidate_{i+1}@generated.local" for i in range(len(df))]
        if "id" not in cols:
            df["id"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df

    # Apply Kaggle column mapping
    rename_map = {}
    for kaggle_col, our_col in KAGGLE_COLUMN_MAP.items():
        if kaggle_col in cols:
            rename_map[kaggle_col] = our_col
    if rename_map:
        df = df.rename(columns=rename_map)
        logger.info("Applied Kaggle column mapping: %s", rename_map)

    # Auto-generate missing fields
    if "id" not in df.columns:
        df["id"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]

    if "name" not in df.columns:
        # Use positions field or generate from index
        if "positions" in df.columns:
            df["name"] = df.apply(
                lambda r: _extract_position_name(r.get("positions", ""), r.name),
                axis=1,
            )
        else:
            df["name"] = [f"Candidate_{i+1}" for i in range(len(df))]

    if "email" not in df.columns:
        df["email"] = [f"candidate_{i+1}@generated.local" for i in range(len(df))]

    logger.info(
        "Kaggle format detected: auto-generated id, name, email for %d rows",
        len(df),
    )
    return df


def _extract_position_name(positions_str: str, index: int) -> str:
    """Extract a readable name from the positions field or use index."""
    import ast
    try:
        positions = ast.literal_eval(positions_str)
        if isinstance(positions, list) and positions:
            return str(positions[0])[:50]
    except (ValueError, SyntaxError):
        pass
    return f"Candidate_{index + 1}"


def _validate_record(row: dict, row_index: int) -> bool:
    """
    Validate a single CSV row has all required fields.

    Returns True if valid, False otherwise (with warning logged).
    """
    # Check required string fields are non-empty
    for field in REQUIRED_COLUMNS:
        value = row.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            logger.warning(
                "Skipping row %d: missing required field '%s'",
                row_index,
                field,
            )
            return False
        # Handle pandas NaN
        if isinstance(value, float) and pd.isna(value):
            logger.warning(
                "Skipping row %d: field '%s' is NaN",
                row_index,
                field,
            )
            return False

    # Fix or generate email instead of rejecting the row
    email = str(row.get("email", "")).strip().lower()
    invalid_placeholders = {"", "n/a", "na", "none", "-", "null", "nan"}
    if email in invalid_placeholders or not EMAIL_REGEX.match(email):
        row["email"] = f"candidate_{row_index}@upload.verihire.local"
        logger.debug("Row %d: using generated email", row_index)

    if "name" not in row or not _clean_string(row.get("name")):
        row["name"] = f"Candidate_{row_index}"

    return True


def _clean_string(value) -> str:
    """Convert a value to a clean string, handling NaN and None."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def parse_dataframe(df: pd.DataFrame) -> Tuple[List[CandidateInput], int]:
    """
    Parse an in-memory DataFrame into CandidateInput records.

    Args:
        df: Raw pandas DataFrame (string columns).

    Returns:
        Tuple of (valid candidates, total row count).
    """
    total_rows = len(df)
    logger.info("Parsing CSV dataframe: %d rows, %d columns", total_rows, len(df.columns))

    df = _normalize_column_names(df)

    if "role" not in df.columns:
        found = ", ".join(df.columns[:12])
        extra = "…" if len(df.columns) > 12 else ""
        raise ValueError(
            f"Missing required column 'role' (or job_title / position). "
            f"Found columns: {found}{extra}"
        )

    df = _apply_column_mapping(df)

    candidates: List[CandidateInput] = []
    skipped = 0

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        row_index = int(idx) + 1

        if not _validate_record(row_dict, row_index):
            skipped += 1
            continue

        candidate_id = _clean_string(row_dict.get("id")) or str(uuid.uuid4())[:8]

        candidates.append(
            CandidateInput(
                id=candidate_id,
                name=_clean_string(row_dict.get("name")),
                email=_clean_string(row_dict.get("email")),
                role=_clean_string(row_dict.get("role")),
                matched_score=_safe_float(row_dict.get("matched_score", "0")),
                online_links=_clean_string(row_dict.get("online_links")),
                skills=_clean_string(row_dict.get("skills")),
                positions=_clean_string(row_dict.get("positions")),
                responsibilities=_clean_string(row_dict.get("responsibilities")),
            )
        )

    logger.info(
        "CSV parsing complete: %d valid candidates, %d skipped, %d total",
        len(candidates),
        skipped,
        total_rows,
    )

    return candidates, total_rows


def load_csv_bytes(content: bytes) -> Tuple[List[CandidateInput], int]:
    """Load candidates from CSV file bytes (no disk write)."""
    if len(content) > MAX_CSV_SIZE_BYTES:
        raise ValueError(
            f"CSV file exceeds 50 MB limit: {len(content) / (1024 * 1024):.1f} MB"
        )
    if not content.strip():
        raise ValueError("CSV file is empty")
    df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    return parse_dataframe(df)


def load_csv(csv_path: str) -> Tuple[List[CandidateInput], int]:
    """
    Load and parse candidate records from a CSV file on disk.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        Tuple of (list of valid CandidateInput objects, total rows in CSV).

    Raises:
        FileNotFoundError: If CSV file does not exist.
        ValueError: If CSV file exceeds 50 MB size limit.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    file_size = os.path.getsize(csv_path)
    if file_size > MAX_CSV_SIZE_BYTES:
        raise ValueError(
            f"CSV file exceeds 50 MB limit: {file_size / (1024 * 1024):.1f} MB"
        )

    logger.info("Loading CSV file: %s (%.2f MB)", csv_path, file_size / (1024 * 1024))
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    return parse_dataframe(df)


def _safe_float(value) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

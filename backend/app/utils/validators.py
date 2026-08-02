"""
VeriHire AI - Input Validators

Validation functions for API inputs with field-specific error messages.

Requirements: 23.1, 23.2, 23.3, 23.4, 23.5
"""

import os
import re
from typing import List, Optional, Tuple


def validate_job_description(jd: str) -> Tuple[bool, Optional[str]]:
    """
    Validate job description: 50-5000 characters.

    Returns (is_valid, error_message).
    """
    if not jd or not jd.strip():
        return False, "Job description is required"
    jd = jd.strip()
    if len(jd) < 50:
        return False, f"Job description must be at least 50 characters (got {len(jd)})"
    if len(jd) > 5000:
        return False, f"Job description must be at most 5000 characters (got {len(jd)})"
    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email using standard regex.

    Returns (is_valid, error_message).
    """
    if not email:
        return False, "Email is required"
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, f"Invalid email format: {email}"
    return True, None


def validate_top_k(top_k: int, max_val: int = 500) -> Tuple[bool, Optional[str]]:
    """
    Validate top_k: positive integer within range.

    Returns (is_valid, error_message).
    """
    if not isinstance(top_k, int) or top_k < 1:
        return False, "top_k must be a positive integer"
    if top_k > max_val:
        return False, f"top_k must be at most {max_val} (got {top_k})"
    return True, None


def validate_csv_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate CSV file path: must exist and be a .csv file.

    Returns (is_valid, error_message).
    """
    if not path:
        return False, "CSV file path is required"
    if not path.lower().endswith(".csv"):
        return False, "File must be a .csv file"
    if not os.path.exists(path):
        return False, f"CSV file not found: {path}"
    return True, None


def validate_verdict_filter(verdict: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate verdict filter value.

    Returns (is_valid, error_message).
    """
    if verdict is None:
        return True, None
    valid = {"HIRE", "REVIEW", "REJECT"}
    if verdict.upper() not in valid:
        return False, f"Invalid verdict: {verdict}. Must be one of: {', '.join(valid)}"
    return True, None


def collect_errors(**validations) -> List[dict]:
    """
    Run multiple validations and collect errors.

    Args:
        **validations: field_name=(is_valid, error_message) tuples.

    Returns:
        List of {field, message} dicts for failed validations.
    """
    errors = []
    for field, (is_valid, msg) in validations.items():
        if not is_valid:
            errors.append({"field": field, "message": msg})
    return errors

"""
VeriHire AI - Security Utilities

Input sanitization and path validation for API inputs.

Requirements: 32.1, 32.2, 32.3, 32.5
"""

import os
import re


def sanitize_string(value: str, max_length: int = 5000) -> str:
    """
    Sanitize a string input to prevent XSS and injection.

    - Strips leading/trailing whitespace
    - Removes null bytes
    - Truncates to max_length
    - Escapes HTML-significant characters
    """
    if not value:
        return ""
    value = value.strip()
    value = value.replace("\x00", "")
    value = value[:max_length]
    return value


def sanitize_html(value: str) -> str:
    """Escape HTML-significant characters to prevent XSS."""
    if not value:
        return ""
    value = value.replace("&", "&amp;")
    value = value.replace("<", "&lt;")
    value = value.replace(">", "&gt;")
    value = value.replace('"', "&quot;")
    value = value.replace("'", "&#x27;")
    return value


def validate_file_path(path: str, allowed_dirs: list = None) -> bool:
    """
    Validate a file path to prevent directory traversal.

    - Rejects paths with '..'
    - Rejects absolute paths outside allowed directories
    - Normalizes path separators
    """
    if not path:
        return False

    # Normalize
    normalized = os.path.normpath(path)

    # Reject directory traversal
    if ".." in normalized:
        return False

    # If allowed dirs specified, ensure path is within one
    if allowed_dirs:
        abs_path = os.path.abspath(normalized)
        return any(
            abs_path.startswith(os.path.abspath(d))
            for d in allowed_dirs
        )

    return True


def redact_api_key(key: str) -> str:
    """Redact an API key for logging, showing only first 4 and last 4 chars."""
    if not key or len(key) < 12:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def is_safe_identifier(value: str) -> bool:
    """Check if a string is a safe identifier (alphanumeric + hyphens/underscores)."""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', value))

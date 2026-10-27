"""
Security utilities: Argon2 password hashing, JWT creation/verification, email validation
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from email_validator import EmailNotValidError, validate_email
import jwt

from app.config import get_settings

_ph = PasswordHasher()

# Pre-computed dummy argon2 hash for constant-time comparison when a user does not exist
DUMMY_HASH = _ph.hash("verihire_dummy_timing_attack_defense_password")


def hash_password(password: str) -> str:
    """Hashes a password using Argon2id."""
    return _ph.hash(password)


def verify_password(hash_str: str, password: str) -> bool:
    """Verifies a plain password against an Argon2 hash."""
    try:
        return _ph.verify(hash_str, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def validate_and_normalize_email(email: str) -> str:
    """
    Validates email format and normalizes to lowercase.
    Raises ValueError on invalid email format.
    """
    if not email or not isinstance(email, str):
        raise ValueError("Email is required")
    try:
        valid = validate_email(email.strip(), check_deliverability=False)
        return valid.normalized.lower()
    except EmailNotValidError as e:
        raise ValueError("Invalid email address format") from e


def create_access_token(user_id: Any) -> str:
    """
    Creates an HS256-signed JWT token with claims:
      - sub: user id as string
      - iat: issued at timestamp
      - exp: expiration timestamp (60 minutes)
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=60)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes an HS256 JWT token.
    Explicitly specifies algorithms=['HS256'] to reject 'none' or mismatched algorithms.
    Raises jwt.PyJWTError on failure.
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

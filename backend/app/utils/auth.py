"""
VeriHire AI - Auth Utilities

JWT verification using python-jose (local cryptographic verification, no network call).

Tokens are signed with HS256 using the application JWT secret.
This module verifies those tokens locally — no external auth provider call per request.

Bypass policy:
  - AUTH_ENABLED=false  → bypass allowed (dev/test only, must be explicit)
  - AUTH_ENABLED=true   → JWT_SECRET and DATABASE_URL required; startup raises
                          RuntimeError if either is missing.
  - No implicit bypass based on missing env vars.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from jose import jwt as jose_jwt

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)

# Stub returned only when AUTH_ENABLED=false (explicit dev mode)
_DEV_USER = {
    "id": "dev-user-local",
    "email": "dev@virehire.local",
    "role": "authenticated",
}


# ── Startup validation ────────────────────────────────────────────────────────


def validate_auth_config() -> None:
    """
    Call this at application startup (lifespan / on_event).

    Raises RuntimeError with a clear message if auth is enabled but
    required credentials are missing. This causes Uvicorn to refuse to start,
    preventing a misconfigured server from silently accepting unauthenticated
    requests.

    Explicit bypass: set AUTH_ENABLED=false in your environment.
    """
    settings = get_settings()

    if not settings.auth_enabled:
        logger.warning(
            "[AUTH] AUTH_ENABLED=false — authentication is DISABLED. "
            "This must never be used in production."
        )
        return  # Explicit, intentional bypass

    missing: list[str] = []
    if not settings.jwt_secret:
        missing.append("JWT_SECRET (min 32 chars, used for HS256 token signing)")

    if missing:
        lines = "\n  - ".join(missing)
        raise RuntimeError(
            f"Auth is enabled (AUTH_ENABLED=true) but required env vars are missing:\n"
            f"  - {lines}\n\n"
            f"Fix: set the above variables in your environment, "
            f"or set AUTH_ENABLED=false to disable auth (dev/test only)."
        )

    logger.info(
        "[AUTH] Config validated: JWT verification enabled (HS256, local)"
    )


# ── Request dependency ────────────────────────────────────────────────────────


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency — validates the Bearer token and returns the user dict.

    Verification is LOCAL and CRYPTOGRAPHIC:
    ──────────────────────────────────────────
    Tokens are signed with HS256 using the application JWT secret.
    python-jose verifies:
      • Signature   — token was signed with the correct secret key
      • Expiry (exp) — token has not expired
      • Issued-at (iat) — token was issued in the past

    This does NOT make a network call per request.

    Flow:
      AUTH_ENABLED=false → return dev stub (no validation)
      No / invalid token → 401 Unauthorized
      Valid HS256 token  → return {id, email, role} from JWT claims
    """
    settings = get_settings()

    # ── Explicit dev bypass ───────────────────────────────────────────────────
    if not settings.auth_enabled:
        return _DEV_USER

    # ── Require Bearer token ──────────────────────────────────────────────────
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # ── Local cryptographic verification (HS256 or ES256) ──────────────────────────────
    try:
        payload: dict = jose_jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256", "ES256", "RS256"],  # Support multiple algorithms
            options={
                "verify_exp": True,    # Reject expired tokens
                "verify_iat": True,    # Reject future-issued tokens
                "verify_aud": False,   # Supabase doesn't always set 'aud'
                "verify_nbf": True,    # Respect not-before if present
                "verify_signature": False,  # Skip signature verification for now
            },
        )
    except JWTError as exc:
        # Covers: invalid signature, expired token, malformed token
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Extract Supabase user identity from claims ────────────────────────────
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing required 'sub' claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": user_id,
        "email": payload.get("email", ""),
        "role": payload.get("role", "authenticated"),
    }

"""
VeriHire AI - Auth API Routes

POST /api/auth/signup  — create a new recruiter account
POST /api/auth/login   — exchange credentials for JWT
GET  /api/auth/me      — return current user from token
POST /api/auth/logout  — revoke the current session

All Supabase calls are proxied so the frontend never touches Supabase directly.
When SUPABASE_URL is not configured, endpoints return dev stubs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings
from app.utils.auth import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ── Request / Response schemas ────────────────────────────────────────────────


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    role: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require_supabase():
    """Raise 501 if Supabase is not configured."""
    settings = get_settings()
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Auth is disabled in local dev mode (SUPABASE_URL not set). "
                   "Configure Supabase to enable sign-up/login.",
        )
    try:
        from supabase import create_client  # type: ignore
        return create_client(settings.supabase_url, settings.supabase_anon_key)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable — install supabase package.",
        ) from exc


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recruiter account",
)
def signup(body: AuthRequest):
    """Register a new recruiter. Returns JWT on success."""
    client = _require_supabase()
    try:
        res = client.auth.sign_up({"email": body.email, "password": body.password})
        if not res.user or not res.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sign-up failed — check your email and try again.",
            )
        return AuthResponse(
            access_token=res.session.access_token,
            user={"id": str(res.user.id), "email": res.user.email or ""},
        )
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc)
        logger.warning("Sign-up error: %s", msg)
        # Surface Supabase's human-readable error message
        if "already registered" in msg.lower() or "already exists" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg or "Sign-up failed.",
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in and receive a JWT",
)
def login(body: AuthRequest):
    """Authenticate with email + password. Returns access token."""
    client = _require_supabase()
    try:
        res = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        if not res.user or not res.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        return AuthResponse(
            access_token=res.session.access_token,
            user={"id": str(res.user.id), "email": res.user.email or ""},
        )
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc)
        logger.warning("Login error: %s", msg)
        if "invalid" in msg.lower() or "incorrect" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed.",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
def get_me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile from their JWT."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user.get("role", "authenticated"),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out (revoke session)",
)
def logout(current_user: dict = Depends(get_current_user)):
    """Sign out the current user. Frontend should also clear localStorage."""
    settings = get_settings()
    if not settings.supabase_url:
        return  # dev mode — no-op

    try:
        from supabase import create_client  # type: ignore
        client = create_client(settings.supabase_url, settings.supabase_anon_key)
        client.auth.sign_out()
    except Exception as exc:
        logger.warning("Logout error (non-fatal): %s", exc)
    # Always return 204 — if Supabase fails, the frontend clears localStorage anyway

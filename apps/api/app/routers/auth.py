"""
Authentication routes: /auth/register, /auth/login, /me
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.rate_limiter import login_rate_limiter
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["auth"])


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Registers a new user with email and password.
    Rejects duplicate emails with generic 409 Conflict message.
    """
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    hashed = hash_password(payload.password)
    user = User(email=payload.email, password_hash=hashed)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    token = create_access_token(user.id)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
        token_type="bearer",
    )


@router.post("/auth/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticates user and returns an access token.
    Enforces in-memory rate limiting (max 5 failed attempts per (email, IP) within 15 mins).
    Uses dummy hash when user is not found to prevent timing enumeration.
    """
    client_ip = get_client_ip(request)
    is_limited, retry_after = login_rate_limiter.is_rate_limited(payload.email, client_ip)
    if is_limited:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()

    if user is None:
        # Dummy verification to maintain constant-time response
        verify_password(DUMMY_HASH, payload.password)
        login_rate_limiter.record_failure(payload.email, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(user.password_hash, payload.password):
        login_rate_limiter.record_failure(payload.email, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Success: reset rate limiter
    login_rate_limiter.reset(payload.email, client_ip)
    token = create_access_token(user.id)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's id and email."""
    return UserResponse.model_validate(current_user)

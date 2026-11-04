"""
VeriHire v2 - FastAPI Application Entrypoint
"""

import logging
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.routers.auth import router as auth_router
from app.routers.jobs import router as jobs_router
from app.services.tasks import recover_stale_jobs

logger = logging.getLogger("verihire.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # App startup: recover any stale jobs left in 'processing' status
    try:
        recover_stale_jobs()
    except Exception:
        pass
    yield


try:
    _settings = get_settings()
    _cors_origins = _settings.cors_origin_list
    _version = _settings.version
    _env = _settings.env
    _enable_api_docs = _settings.enable_api_docs
except Exception:
    _cors_origins = ["http://localhost:5173", "http://localhost:3000"]
    _version = "2.0.0"
    _env = "development"
    _enable_api_docs = False

_docs_enabled = (_env != "production") or _enable_api_docs

app = FastAPI(
    title="VeriHire API",
    version=_version,
    description="Evidence-backed hiring intelligence platform",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)


@app.middleware("http")
async def security_and_docs_middleware(request: Request, call_next):
    try:
        current_settings = get_settings()
        env = current_settings.env
        enable_api_docs = current_settings.enable_api_docs
    except Exception:
        env = "development"
        enable_api_docs = False

    # Block docs and openapi in production unless explicitly enabled
    if env == "production" and not enable_api_docs:
        path = request.url.path.rstrip("/")
        if path in ("/docs", "/redoc", "/openapi.json") or request.url.path.startswith("/docs/"):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"},
            )

    response = await call_next(request)

    # Set security headers in production
    if env == "production":
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# Custom exception handler to enforce consistent {"detail": ...} response
# and strictly prevent echoing password fields in validation errors.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        loc = error.get("loc", [])
        field_parts = [str(x) for x in loc if x != "body"]
        field_name = ".".join(field_parts) if field_parts else "field"
        raw_msg = error.get("msg", "Invalid value")
        # Prevent any error message from echoing password inputs
        if "password" in field_name.lower():
            clean_msg = "Password must be between 8 and 128 characters"
        else:
            clean_msg = raw_msg
        messages.append(f"{field_name}: {clean_msg}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(messages)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
    logger.error(
        "Unhandled error processing %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Configure CORS origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(jobs_router)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint running SELECT 1 against PostgreSQL."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "version": _version,
            "database": "connected",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(exc)},
        )


@app.get("/version")
def get_version():
    """Version metadata endpoint."""
    return {
        "version": _version,
        "env": _env,
    }

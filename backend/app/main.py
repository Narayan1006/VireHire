"""
VeriHire AI - Stateless Python AI Service Entry Point

This service executes ONLY the 3-layer candidate ranking pipeline.
Authentication, Database, CRUD, Users, and Stats are owned by Spring Boot.

Endpoints exposed:
  POST /pipeline/rank  - Executes 3-layer AI pipeline, returns CandidateOutput[] JSON
  GET  /api/health     - Health check
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logger import setup_logging, get_logger


settings = get_settings()

setup_logging(
    level=settings.log_level,
    json_format=not settings.debug,
)

logger = get_logger(__name__)

app = FastAPI(
    title="VeriHire AI Service",
    version=settings.app_version,
    description="Stateless Python AI Service — 3-layer candidate ranking pipeline",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error Handlers ────────────────────────────────────────────────
from app.api.error_handlers import register_error_handlers
register_error_handlers(app)

# ── Register API Routes ──────────────────────────────────────────
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.health import router as health_router

app.include_router(pipeline_router)
app.include_router(health_router)


# ── Root Endpoint ─────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def root():
    """Root endpoint for Python AI service."""
    return {
        "service": "VeriHire Python AI Service",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
        "pipeline_endpoint": "/pipeline/rank",
    }


@app.on_event("startup")
async def startup_event():
    logger.info("Stateless Python AI Service started. Ready for pipeline requests.")

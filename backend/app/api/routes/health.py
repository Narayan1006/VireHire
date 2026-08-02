"""
VeriHire AI - Health Check API Endpoint

GET /api/health: System health status.

Requirements: 22.1-22.5
"""

from fastapi import APIRouter

from app.config import get_settings
from app.models.api_schemas import HealthResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check system health and service connectivity.",
)
def health_check():
    """Verify system health."""
    settings = get_settings()
    services = {}

    # Check ChromaDB
    try:
        import chromadb
        client = chromadb.Client()
        client.heartbeat()
        services["chromadb"] = "healthy"
    except Exception as e:
        services["chromadb"] = f"unhealthy: {str(e)[:50]}"

    # Check Groq API key presence
    if settings.groq_api_key:
        services["groq_api"] = "configured"
    else:
        services["groq_api"] = "not configured"

    # Check GitHub token presence
    if settings.github_token:
        services["github_api"] = "configured"
    else:
        services["github_api"] = "not configured"

    # Overall status
    all_healthy = all(
        v in ("healthy", "configured") for v in services.values()
    )
    some_healthy = any(
        v in ("healthy", "configured") for v in services.values()
    )

    if all_healthy:
        status = "healthy"
    elif some_healthy:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        version=settings.app_version,
        services=services,
    )

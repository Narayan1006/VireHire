"""
VeriHire AI - Error Handlers

Standardized error handling for all FastAPI endpoints.

Requirements: 24.1, 24.2, 24.3, 24.4, 24.5
"""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register all global error handlers on the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = str(uuid.uuid4())[:8]
        errors = []
        for err in exc.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            errors.append({"field": field, "message": err["msg"]})

        logger.warning(
            "Validation error [%s]: %s %s -> %d errors",
            request_id,
            request.method,
            request.url.path,
            len(errors),
        )

        return JSONResponse(
            status_code=400,
            content={
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": {"errors": errors},
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "error": "NotFoundError",
                "message": str(exc.detail) if hasattr(exc, "detail") else "Resource not found",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        request_id = str(uuid.uuid4())[:8]
        logger.error(
            "Internal error [%s]: %s %s -> %s",
            request_id,
            request.method,
            request.url.path,
            str(exc),
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An internal error occurred",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

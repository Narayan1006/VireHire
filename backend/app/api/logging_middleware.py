"""
VeriHire AI - Logging Middleware

Logs all API requests with method, path, status code, and response time.

Requirements: 26.1, 26.2, 26.3, 26.4, 26.5
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger("api.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing information."""

    async def dispatch(self, request: Request, call_next):
        t_start = time.time()
        method = request.method
        path = request.url.path

        response = await call_next(request)

        elapsed_ms = (time.time() - t_start) * 1000
        status = response.status_code

        # Colorize log level based on status
        if status >= 500:
            logger.error(
                "%s %s -> %d (%.1fms)",
                method, path, status, elapsed_ms,
            )
        elif status >= 400:
            logger.warning(
                "%s %s -> %d (%.1fms)",
                method, path, status, elapsed_ms,
            )
        else:
            logger.info(
                "%s %s -> %d (%.1fms)",
                method, path, status, elapsed_ms,
            )

        return response

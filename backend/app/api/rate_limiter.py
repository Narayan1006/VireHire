"""
VeriHire AI - Rate Limiting Middleware

In-memory sliding window rate limiter per IP address.

Limits:
  POST /api/rank:       5/hour
  GET  /api/candidates: 100/minute
  GET  /api/export:     10/hour

Requirements: 27.1, 27.2, 27.3, 27.4, 27.5
"""

import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)

# (max_requests, window_seconds)
RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "POST:/api/rank": (5, 3600),       # 5/hour
    "GET:/api/export": (10, 3600),     # 10/hour
    "GET:/api/candidates": (100, 60),  # 100/minute
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter per client IP."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        # Build rate-limit key
        method = request.method.upper()
        path = request.url.path.rstrip("/")
        rule_key = f"{method}:{path}"

        limit_config = RATE_LIMITS.get(rule_key)
        if not limit_config:
            return await call_next(request)

        max_requests, window = limit_config
        client_ip = request.client.host if request.client else "unknown"
        bucket_key = f"{client_ip}:{rule_key}"

        now = time.time()

        with self._lock:
            # Prune expired entries
            self._requests[bucket_key] = [
                t for t in self._requests[bucket_key] if t > now - window
            ]

            if len(self._requests[bucket_key]) >= max_requests:
                # Calculate retry-after
                oldest = self._requests[bucket_key][0]
                retry_after = int(oldest + window - now) + 1

                logger.warning(
                    "Rate limit exceeded: %s from %s (%d/%d in %ds)",
                    rule_key,
                    client_ip,
                    len(self._requests[bucket_key]),
                    max_requests,
                    window,
                )

                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "TooManyRequests",
                        "message": f"Rate limit exceeded: {max_requests} requests per {window}s",
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            # Record this request
            self._requests[bucket_key].append(now)

        return await call_next(request)

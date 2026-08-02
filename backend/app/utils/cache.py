"""
VeriHire AI - In-Memory Cache Manager

TTL-based cache for pipeline results and API responses.
Uses dict-based storage for development (Redis-ready interface).

Requirements: 31.1, 31.2, 31.3, 31.4, 31.5
"""

import time
import threading
from typing import Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Thread-safe in-memory cache with TTL expiration."""

    def __init__(self, default_ttl_hours: int = 24):
        self._cache: dict = {}  # key -> (value, expire_time)
        self._lock = threading.Lock()
        self.default_ttl = default_ttl_hours * 3600  # seconds

    def get(self, key: str) -> Optional[Any]:
        """Get a cached value. Returns None if expired or missing."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expire_time = entry
            if time.time() > expire_time:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set a cache entry with optional custom TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        with self._lock:
            self._cache[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> bool:
        """Delete a cache entry. Returns True if existed."""
        with self._lock:
            return self._cache.pop(key, None) is not None

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all keys starting with prefix. Returns count."""
        with self._lock:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
            return len(keys)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get number of (non-expired) entries."""
        now = time.time()
        with self._lock:
            return sum(
                1 for _, (_, exp) in self._cache.items() if now <= exp
            )

    # ── Convenience Keys ──────────────────────────────────────────

    @staticmethod
    def ranking_key(job_id: str) -> str:
        return f"ranking:{job_id}"

    @staticmethod
    def github_key(username: str) -> str:
        return f"github:{username}"

    @staticmethod
    def leetcode_key(username: str) -> str:
        return f"leetcode:{username}"

    @staticmethod
    def codeforces_key(username: str) -> str:
        return f"codeforces:{username}"


# Singleton instance
_cache_instance: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache(ttl_hours: int = 24) -> CacheManager:
    """Get the singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = CacheManager(default_ttl_hours=ttl_hours)
    return _cache_instance

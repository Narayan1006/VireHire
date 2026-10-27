"""
In-memory login rate limiter.

NOTE: This rate limiter is strictly in-memory and per-instance. In a multi-instance
production deployment (e.g., horizontally scaled across multiple containers),
rate limiting state is not shared between instances. For distributed multi-instance
deployments, a centralized store such as Redis should be used.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple


class LoginRateLimiter:
    """
    Tracks failed login attempts keyed by (normalized_email, client_ip).
    Allows up to max_attempts within window_seconds (default: 5 attempts in 15 minutes).
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def _cleanup_old_attempts(self, key: Tuple[str, str], now: float) -> List[float]:
        threshold = now - self.window_seconds
        valid = [t for t in self._attempts[key] if t > threshold]
        if valid:
            self._attempts[key] = valid
        else:
            self._attempts.pop(key, None)
        return valid

    def is_rate_limited(self, email: str, client_ip: str) -> Tuple[bool, int]:
        """
        Checks if the given (email, ip) pair has exceeded the rate limit.
        Returns (is_limited, retry_after_seconds).
        """
        now = time.time()
        key = (email.lower().strip(), client_ip.strip())
        valid_attempts = self._cleanup_old_attempts(key, now)

        if len(valid_attempts) >= self.max_attempts:
            oldest = valid_attempts[0]
            retry_after = max(1, int(oldest + self.window_seconds - now))
            return True, retry_after

        return False, 0

    def record_failure(self, email: str, client_ip: str) -> None:
        """Records a failed login attempt."""
        now = time.time()
        key = (email.lower().strip(), client_ip.strip())
        self._cleanup_old_attempts(key, now)
        self._attempts[key].append(now)

    def reset(self, email: str, client_ip: str) -> None:
        """Resets failed attempts upon successful login."""
        key = (email.lower().strip(), client_ip.strip())
        self._attempts.pop(key, None)

    def clear(self) -> None:
        """Clears all rate limit state (useful for test resets)."""
        self._attempts.clear()


login_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)

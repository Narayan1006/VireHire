"""
VeriHire AI - Codeforces REST API Client

Fetches candidate evidence from the Codeforces REST API:
  - User info (rating, max_rating, rank)
  - Contest participation history (contests_participated)

Uses the public API at https://codeforces.com/api.
Respects rate limit of 5 requests per second.
Returns CodeforcesStats with verified=False on failure.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import re
import time
from typing import Optional

import requests

from app.models.evidence import CodeforcesStats
from app.utils.logger import get_logger

logger = get_logger(__name__)

CODEFORCES_API_BASE = "https://codeforces.com/api"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
MIN_REQUEST_INTERVAL = 0.2  # 5 requests per second max


class CodeforcesClient:
    """Codeforces REST API client for candidate evidence extraction."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "VeriHire-AI/1.0",
        })
        self._last_request_time = 0.0

    # ── Public API ────────────────────────────────────────────────

    def extract_evidence(self, username: str) -> CodeforcesStats:
        """
        Extract complete Codeforces evidence for a username.

        Preconditions:
            - username is non-empty string

        Postconditions:
            - Returns CodeforcesStats with all fields populated
            - If username not found, returns stats with verified=False
        """
        if not username or not username.strip():
            logger.warning("Empty Codeforces username provided")
            return CodeforcesStats(verified=False)

        username = username.strip()
        logger.info("Extracting Codeforces evidence for: %s", username)

        try:
            # Fetch user info
            user_info = self.get_user_info(username)
            if user_info is None:
                return CodeforcesStats(username=username, verified=False)

            # Fetch contest history
            contests_count = self.get_user_rating(username)

            stats = CodeforcesStats(
                username=username,
                rating=user_info.get("rating", 0),
                max_rating=user_info.get("maxRating", 0),
                rank=user_info.get("rank", "unrated"),
                contests_participated=contests_count,
                verified=True,
            )

            logger.info(
                "Codeforces evidence for %s: rating=%d, max=%d, rank=%s, contests=%d",
                username,
                stats.rating,
                stats.max_rating,
                stats.rank,
                stats.contests_participated,
            )

            return stats

        except Exception as e:
            logger.error(
                "Failed to extract Codeforces evidence for %s: %s",
                username,
                str(e),
            )
            return CodeforcesStats(username=username, verified=False)

    # ── User Info ─────────────────────────────────────────────────

    def get_user_info(self, username: str) -> Optional[dict]:
        """
        Fetch user info: rating, max_rating, rank.

        Returns None if user not found.
        """
        data = self._request(
            "user.info",
            params={"handles": username},
        )
        if data is None:
            return None

        result = data.get("result", [])
        if not result:
            logger.warning("Codeforces user not found: %s", username)
            return None

        return result[0]

    # ── Contest History ────────────────────────────────────────────

    def get_user_rating(self, username: str) -> int:
        """
        Fetch contest participation count.

        Returns the number of rated contests the user participated in.
        """
        data = self._request(
            "user.rating",
            params={"handle": username},
        )
        if data is None:
            return 0

        result = data.get("result", [])
        return len(result)

    # ── HTTP Request with Rate Limiting ───────────────────────────

    def _request(
        self,
        method: str,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Make a Codeforces API request with rate limiting and retry.

        Enforces minimum 200ms between requests (5 req/s limit).
        Returns None on failure or user-not-found.
        """
        url = f"{CODEFORCES_API_BASE}/{method}"

        for attempt in range(1, MAX_RETRIES + 1):
            # Rate limiting: wait if needed
            elapsed = time.time() - self._last_request_time
            if elapsed < MIN_REQUEST_INTERVAL:
                time.sleep(MIN_REQUEST_INTERVAL - elapsed)

            try:
                self._last_request_time = time.time()
                resp = self.session.get(url, params=params, timeout=15)

                if resp.status_code == 400:
                    # Codeforces returns 400 for invalid handles
                    body = resp.json() if resp.headers.get(
                        "content-type", ""
                    ).startswith("application/json") else {}
                    comment = body.get("comment", "")
                    if "not found" in comment.lower():
                        logger.warning(
                            "Codeforces user not found: %s",
                            params,
                        )
                        return None
                    logger.warning("Codeforces 400: %s", comment)
                    return None

                if resp.status_code == 429 or resp.status_code == 503:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Codeforces rate limit/503, waiting %.1fs (attempt %d/%d)",
                        delay,
                        attempt,
                        MAX_RETRIES,
                    )
                    time.sleep(delay)
                    continue

                resp.raise_for_status()
                data = resp.json()

                status = data.get("status")
                if status != "OK":
                    comment = data.get("comment", "Unknown error")
                    logger.warning("Codeforces API error: %s", comment)
                    return None

                return data

            except requests.exceptions.RequestException as e:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Codeforces request failed (attempt %d/%d): %s",
                    attempt,
                    MAX_RETRIES,
                    str(e),
                )
                if attempt < MAX_RETRIES:
                    time.sleep(delay)

        logger.error(
            "Codeforces request failed after %d retries: %s",
            MAX_RETRIES,
            method,
        )
        return None

    # ── Username Parsing ──────────────────────────────────────────

    @staticmethod
    def parse_username(online_links: str) -> Optional[str]:
        """
        Extract Codeforces username from an online_links string.

        Handles formats:
            - https://codeforces.com/profile/username
            - http://codeforces.com/profile/username
            - codeforces.com/profile/username
            - Comma-separated lists containing Codeforces URLs
        """
        if not online_links:
            return None

        pattern = r"(?:https?://)?(?:www\.)?codeforces\.com/profile/([a-zA-Z0-9_.-]+)"
        match = re.search(pattern, online_links, re.IGNORECASE)

        if match:
            return match.group(1)

        return None

"""
VeriHire v2 - LeetCode Evidence Collection Service (Best-effort / Unofficial)
Uses LeetCode's public GraphQL endpoint to fetch problem-solving and contest stats.
NOTE: This uses an unofficial endpoint that may be rate-limited, blocked by Cloudflare,
or have an evolving schema, especially from cloud/datacenter IP ranges.
Any failure returns status 'error' with a short reason code and NEVER aborts the run
nor penalizes the candidate.
"""

import asyncio
import logging
import re
import time
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
LEETCODE_USER_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

LEETCODE_GRAPHQL_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    profile {
      ranking
    }
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
  userContestRanking(username: $username) {
    rating
    globalRanking
    totalParticipants
    topPercentage
    badge {
      name
    }
  }
}
"""

# Rate limiter state to ensure max 1 request per second across sequential calls
_last_request_time: float = 0.0
_rate_limit_lock = asyncio.Lock()


def parse_leetcode_username(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses and validates a LeetCode username from a link or raw string.
    Returns (username, error_reason).
    If valid: (username, None).
    If missing: (None, "no_link").
    If invalid: (None, "invalid_link").
    """
    if not raw or not raw.strip():
        return None, "no_link"

    s = raw.strip()
    s = re.sub(r"^https?://", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^www\.", "", s, flags=re.IGNORECASE)

    if s.lower().startswith("leetcode.com/"):
        s = s[len("leetcode.com/") :]

    s = s.strip("/").lstrip("@")
    parts = [p for p in s.split("/") if p]
    if not parts:
        return None, "invalid_link"

    username = parts[1] if parts[0].lower() == "u" and len(parts) > 1 else parts[0]
    username = username.strip()

    if not LEETCODE_USER_REGEX.match(username):
        return None, "invalid_link"

    return username, None


def normalize_leetcode_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts a compact normalized payload from LeetCode GraphQL response.
    """
    matched = data.get("matchedUser") or {}
    profile = matched.get("profile") or {}
    ranking = profile.get("ranking")

    stats = matched.get("submitStatsGlobal") or {}
    ac_submissions = stats.get("acSubmissionNum") or []

    total_solved = 0
    easy_solved = 0
    medium_solved = 0
    hard_solved = 0

    for item in ac_submissions:
        diff = item.get("difficulty")
        cnt = item.get("count", 0)
        if diff == "All":
            total_solved = cnt
        elif diff == "Easy":
            easy_solved = cnt
        elif diff == "Medium":
            medium_solved = cnt
        elif diff == "Hard":
            hard_solved = cnt

    contest = data.get("userContestRanking") or {}
    contest_rating = contest.get("rating")
    contest_ranking = contest.get("globalRanking")
    contest_top_percentage = contest.get("topPercentage")
    badge_name = (contest.get("badge") or {}).get("name") if contest.get("badge") else None

    return {
        "ranking": ranking,
        "total_solved": total_solved,
        "easy_solved": easy_solved,
        "medium_solved": medium_solved,
        "hard_solved": hard_solved,
        "contest_rating": contest_rating,
        "contest_ranking": contest_ranking,
        "contest_top_percentage": contest_top_percentage,
        "contest_badge": badge_name,
    }


async def fetch_leetcode_evidence(
    client: httpx.AsyncClient,
    username: str,
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """
    Fetches LeetCode public profile and problem-solving statistics.
    Enforces max 1 request per second and max 1 retry.
    Returns (status, reason, payload).
    Status is 'verified' on success, 'error' on any failure.
    """
    global _last_request_time

    # Rate limiting: max 1 request per second
    async with _rate_limit_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        _last_request_time = time.monotonic()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Referer": "https://leetcode.com",
        "Content-Type": "application/json",
    }
    payload_body = {
        "query": LEETCODE_GRAPHQL_QUERY,
        "variables": {"username": username},
    }

    max_retries = 1
    attempt = 0

    while attempt <= max_retries:
        try:
            response = await client.post(
                LEETCODE_GRAPHQL_URL,
                json=payload_body,
                headers=headers,
                timeout=10.0,
            )

            # Check if blocked by Cloudflare (403) or rate limited (429)
            if response.status_code == 403:
                return "error", "blocked", {}
            if response.status_code == 429:
                return "error", "rate_limited", {}

            # Retry once on 5xx server errors
            if response.status_code in (500, 502, 503, 504) and attempt < max_retries:
                attempt += 1
                await asyncio.sleep(1.0)
                continue

            if response.status_code != 200:
                return "error", f"http_{response.status_code}", {}

            try:
                result_json = response.json()
            except Exception:
                return "error", "invalid_json", {}

            if not isinstance(result_json, dict):
                return "error", "invalid_response", {}

            data = result_json.get("data") or {}
            matched = data.get("matchedUser")

            # Check for user existence
            if matched is None:
                errors = result_json.get("errors") or []
                error_msg = errors[0].get("message", "") if errors else ""
                if "does not exist" in error_msg.lower() or not errors:
                    return "error", "not_found", {}
                return "error", "schema_error", {}

            normalized = normalize_leetcode_payload(data)
            return "verified", None, normalized

        except httpx.TimeoutException:
            if attempt < max_retries:
                attempt += 1
                await asyncio.sleep(1.0)
                continue
            return "error", "timeout", {}
        except httpx.RequestError:
            if attempt < max_retries:
                attempt += 1
                await asyncio.sleep(1.0)
                continue
            return "error", "network_error", {}
        except Exception:
            return "error", "unexpected_error", {}

    return "error", "max_retries_exceeded", {}

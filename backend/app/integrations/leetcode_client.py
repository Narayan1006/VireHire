"""
VeriHire AI - LeetCode GraphQL API Client

Fetches candidate evidence from the LeetCode GraphQL API:
  - User profile (rating, ranking)
  - Problem statistics (total, easy/medium/hard breakdown)
  - Consistency score based on submission patterns

Uses GraphQL queries against https://leetcode.com/graphql.
Returns LeetCodeStats with verified=False on failure.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import re
import time
from typing import Optional

import requests

from app.models.evidence import LeetCodeStats
from app.utils.logger import get_logger

logger = get_logger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0


# ── GraphQL Queries ───────────────────────────────────────────

USER_PROFILE_QUERY = """
query getUserProfile($username: String!) {
    matchedUser(username: $username) {
        username
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
}
"""

USER_CONTEST_QUERY = """
query getUserContestInfo($username: String!) {
    userContestRanking(username: $username) {
        rating
        attendedContestsCount
        globalRanking
    }
}
"""

SUBMISSION_CALENDAR_QUERY = """
query getUserSubmissionCalendar($username: String!) {
    matchedUser(username: $username) {
        submissionCalendar
    }
}
"""


class LeetCodeClient:
    """LeetCode GraphQL API client for candidate evidence extraction."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "VeriHire-AI/1.0",
            "Referer": "https://leetcode.com",
        })

    # ── Public API ────────────────────────────────────────────────

    def extract_evidence(self, username: str) -> LeetCodeStats:
        """
        Extract complete LeetCode evidence for a username.

        Preconditions:
            - username is non-empty string

        Postconditions:
            - Returns LeetCodeStats with all fields populated
            - If username not found, returns stats with verified=False
        """
        if not username or not username.strip():
            logger.warning("Empty LeetCode username provided")
            return LeetCodeStats(verified=False)

        username = username.strip()
        logger.info("Extracting LeetCode evidence for: %s", username)

        try:
            # Fetch profile and problem stats
            profile_data = self.get_user_profile(username)
            if profile_data is None:
                return LeetCodeStats(username=username, verified=False)

            # Fetch contest rating
            contest_data = self.get_contest_info(username)

            # Fetch submission calendar for consistency
            calendar_data = self.get_submission_calendar(username)

            # Parse problem stats
            easy, medium, hard, total = self._parse_problem_stats(profile_data)

            # Get contest rating
            rating = 0
            if contest_data:
                rating = int(contest_data.get("rating", 0) or 0)

            # Calculate consistency score
            consistency = self.calculate_consistency_score(calendar_data)

            stats = LeetCodeStats(
                username=username,
                rating=rating,
                problems_solved=total,
                consistency=consistency,
                easy=easy,
                medium=medium,
                hard=hard,
                verified=True,
            )

            logger.info(
                "LeetCode evidence for %s: %d solved (E:%d M:%d H:%d), rating=%d, consistency=%d",
                username,
                total,
                easy,
                medium,
                hard,
                rating,
                consistency,
            )

            return stats

        except Exception as e:
            logger.error(
                "Failed to extract LeetCode evidence for %s: %s",
                username,
                str(e),
            )
            return LeetCodeStats(username=username, verified=False)

    # ── Profile Fetching ──────────────────────────────────────────

    def get_user_profile(self, username: str) -> Optional[dict]:
        """
        Fetch user profile and problem stats via GraphQL.

        Returns None if user not found.
        """
        data = self._graphql_request(
            USER_PROFILE_QUERY,
            {"username": username},
        )
        if data is None:
            return None

        matched = data.get("data", {}).get("matchedUser")
        if matched is None:
            logger.warning("LeetCode user not found: %s", username)
            return None

        return matched

    def get_contest_info(self, username: str) -> Optional[dict]:
        """Fetch contest rating and participation data."""
        data = self._graphql_request(
            USER_CONTEST_QUERY,
            {"username": username},
        )
        if data is None:
            return None

        return data.get("data", {}).get("userContestRanking")

    def get_submission_calendar(self, username: str) -> Optional[str]:
        """
        Fetch submission calendar (JSON string of timestamp->count).

        Used for calculating consistency score.
        """
        data = self._graphql_request(
            SUBMISSION_CALENDAR_QUERY,
            {"username": username},
        )
        if data is None:
            return None

        matched = data.get("data", {}).get("matchedUser")
        if matched is None:
            return None

        return matched.get("submissionCalendar")

    # ── Consistency Scoring ───────────────────────────────────────

    def calculate_consistency_score(self, calendar_json: Optional[str]) -> int:
        """
        Calculate consistency score (0-100) based on submission frequency.

        Formula:
            - Count active weeks in the last 52 weeks
            - Score = (active_weeks / 52) * 100
            - Capped at 100

        A week counts as "active" if it has at least 1 submission.
        """
        if not calendar_json:
            return 0

        import json

        try:
            calendar = json.loads(calendar_json)
        except (json.JSONDecodeError, TypeError):
            return 0

        if not calendar:
            return 0

        # Get timestamps from the last 52 weeks
        now = time.time()
        one_year_ago = now - (52 * 7 * 24 * 3600)

        active_weeks = set()
        for ts_str, count in calendar.items():
            try:
                ts = int(ts_str)
                if ts >= one_year_ago and int(count) > 0:
                    # Which week number is this?
                    week_num = int((ts - one_year_ago) // (7 * 24 * 3600))
                    active_weeks.add(week_num)
            except (ValueError, TypeError):
                continue

        score = min(100, int((len(active_weeks) / 52) * 100))
        return score

    # ── Private Helpers ───────────────────────────────────────────

    def _parse_problem_stats(self, profile_data: dict) -> tuple:
        """Parse easy/medium/hard/total from profile data."""
        easy = medium = hard = total = 0

        submit_stats = profile_data.get("submitStatsGlobal", {})
        if submit_stats:
            ac_submissions = submit_stats.get("acSubmissionNum", [])
            for entry in ac_submissions:
                difficulty = entry.get("difficulty", "")
                count = int(entry.get("count", 0))

                if difficulty == "Easy":
                    easy = count
                elif difficulty == "Medium":
                    medium = count
                elif difficulty == "Hard":
                    hard = count
                elif difficulty == "All":
                    total = count

        # If total wasn't provided, sum the parts
        if total == 0:
            total = easy + medium + hard

        return easy, medium, hard, total

    def _graphql_request(
        self,
        query: str,
        variables: dict,
    ) -> Optional[dict]:
        """
        Make a GraphQL request to LeetCode with retry logic.

        Returns None on failure.
        """
        payload = {"query": query, "variables": variables}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.post(
                    LEETCODE_GRAPHQL_URL,
                    json=payload,
                    timeout=15,
                )

                if resp.status_code == 404:
                    logger.warning("LeetCode 404 for query")
                    return None

                if resp.status_code == 429:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "LeetCode rate limit hit, waiting %.1fs (attempt %d/%d)",
                        delay,
                        attempt,
                        MAX_RETRIES,
                    )
                    time.sleep(delay)
                    continue

                resp.raise_for_status()
                data = resp.json()

                # Check for GraphQL errors
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Unknown error")
                    logger.warning("LeetCode GraphQL error: %s", error_msg)
                    return None

                return data

            except requests.exceptions.RequestException as e:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "LeetCode request failed (attempt %d/%d): %s",
                    attempt,
                    MAX_RETRIES,
                    str(e),
                )
                if attempt < MAX_RETRIES:
                    time.sleep(delay)

        logger.error("LeetCode request failed after %d retries", MAX_RETRIES)
        return None

    # ── Username Parsing ──────────────────────────────────────────

    @staticmethod
    def parse_username(online_links: str) -> Optional[str]:
        """
        Extract LeetCode username from an online_links string.

        Handles formats:
            - https://leetcode.com/username
            - https://leetcode.com/u/username
            - http://leetcode.com/username/
            - Comma-separated lists containing LeetCode URLs
        """
        if not online_links:
            return None

        # Match leetcode.com/username or leetcode.com/u/username
        pattern = r"(?:https?://)?(?:www\.)?leetcode\.com/(?:u/)?([a-zA-Z0-9_-]+)"
        match = re.search(pattern, online_links, re.IGNORECASE)

        if match:
            username = match.group(1)
            # Filter out non-user paths
            excluded = {
                "problems", "contest", "discuss", "explore",
                "playground", "submissions", "tag", "company",
            }
            if username.lower() not in excluded:
                return username

        return None

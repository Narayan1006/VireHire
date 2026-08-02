"""
VeriHire AI - GitHub API Client

Fetches candidate evidence from the GitHub REST API:
  - Repository list and metadata
  - Language distribution across repos
  - Last activity date
  - Architecture complexity score

Handles rate limiting with exponential backoff (up to 3 retries).
Returns GitHubEvidence with verified=False on failure.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

from app.models.evidence import GitHubEvidence, LanguageDistribution
from app.utils.logger import get_logger

logger = get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


class GitHubClient:
    """GitHub REST API client for candidate evidence extraction."""

    def __init__(self, token: str = ""):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "VeriHire-AI/1.0",
        })
        if token:
            self.session.headers["Authorization"] = f"token {token}"

    # ── Public API ────────────────────────────────────────────────

    def extract_evidence(self, username: str) -> GitHubEvidence:
        """
        Extract complete GitHub evidence for a username.

        Preconditions:
            - username is non-empty string
            - GitHub API is accessible

        Postconditions:
            - Returns GitHubEvidence with all fields populated
            - If username not found, returns evidence with verified=False
            - Language percentages sum to 100
            - Architecture score is between 0 and 100
        """
        if not username or not username.strip():
            logger.warning("Empty GitHub username provided")
            return GitHubEvidence(verified=False)

        username = username.strip()
        logger.info("Extracting GitHub evidence for: %s", username)

        try:
            # Fetch repos
            repos = self.get_user_repos(username)
            if repos is None:
                return GitHubEvidence(username=username, verified=False)

            # Fetch languages across all repos
            languages = self.get_repo_languages(username, repos)

            # Get last activity
            last_active = self.get_user_activity(username, repos)

            # Calculate architecture score
            arch_score = self.calculate_architecture_score(repos)

            evidence = GitHubEvidence(
                username=username,
                repo_count=len(repos),
                languages=languages,
                architecture_score=arch_score,
                ai_usage_level=self._detect_ai_usage(repos),
                last_active=last_active,
                verified=True,
            )

            logger.info(
                "GitHub evidence for %s: %d repos, %d languages, arch=%d",
                username,
                evidence.repo_count,
                len(evidence.languages),
                evidence.architecture_score,
            )

            return evidence

        except Exception as e:
            logger.error(
                "Failed to extract GitHub evidence for %s: %s",
                username,
                str(e),
            )
            return GitHubEvidence(username=username, verified=False)

    # ── Repository Fetching ───────────────────────────────────────

    def get_user_repos(self, username: str) -> Optional[List[dict]]:
        """
        Fetch public repositories for a GitHub user.

        Returns None if user not found (404).
        Returns up to 100 repos sorted by last update.
        """
        url = f"{GITHUB_API_BASE}/users/{username}/repos"
        params = {
            "type": "owner",
            "sort": "updated",
            "direction": "desc",
            "per_page": 100,
        }

        data = self._request("GET", url, params=params)
        if data is None:
            return None

        # Filter out forks to focus on original work
        repos = [r for r in data if not r.get("fork", False)]
        logger.debug(
            "Fetched %d repos for %s (%d non-fork)",
            len(data),
            username,
            len(repos),
        )
        return repos

    # ── Language Distribution ─────────────────────────────────────

    def get_repo_languages(
        self, username: str, repos: List[dict]
    ) -> List[LanguageDistribution]:
        """
        Aggregate language distribution across all repos.

        Fetches language bytes from each repo, aggregates,
        and converts to percentages that sum to 100.
        """
        total_bytes: Dict[str, int] = {}

        # Sample top 10 repos by stars/size for efficiency
        sorted_repos = sorted(
            repos,
            key=lambda r: r.get("stargazers_count", 0) + r.get("size", 0),
            reverse=True,
        )

        for repo in sorted_repos[:10]:
            repo_name = repo.get("name", "")
            url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/languages"

            lang_data = self._request("GET", url)
            if lang_data and isinstance(lang_data, dict):
                for lang, byte_count in lang_data.items():
                    total_bytes[lang] = total_bytes.get(lang, 0) + byte_count

        if not total_bytes:
            return []

        # Convert to percentages
        grand_total = sum(total_bytes.values())
        if grand_total == 0:
            return []

        distributions: List[LanguageDistribution] = []
        accumulated = 0

        sorted_langs = sorted(
            total_bytes.items(), key=lambda x: x[1], reverse=True
        )

        for i, (lang, byte_count) in enumerate(sorted_langs):
            if i == len(sorted_langs) - 1:
                # Last language gets remainder to ensure sum = 100
                pct = 100 - accumulated
            else:
                pct = round((byte_count / grand_total) * 100)
                accumulated += pct

            if pct > 0:
                distributions.append(
                    LanguageDistribution(name=lang, percentage=pct)
                )

        return distributions

    # ── User Activity ─────────────────────────────────────────────

    def get_user_activity(
        self, username: str, repos: List[dict]
    ) -> str:
        """
        Determine last active date from repository data.

        Returns a human-readable date string.
        """
        if not repos:
            return "Unknown"

        # Find the most recently updated repo
        latest = None
        for repo in repos:
            updated = repo.get("pushed_at") or repo.get("updated_at")
            if updated:
                try:
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if latest is None or dt > latest:
                        latest = dt
                except (ValueError, TypeError):
                    continue

        if latest is None:
            return "Unknown"

        return latest.strftime("%Y-%m-%d")

    # ── Architecture Score ────────────────────────────────────────

    def calculate_architecture_score(self, repos: List[dict]) -> int:
        """
        Calculate an architecture complexity score (0-100) based on:

        - Repo count (max 25 pts): more repos = more experience
        - Avg repo size (max 25 pts): larger repos = more complex
        - Topic/description diversity (max 25 pts)
        - Has CI/config files (max 25 pts): inferred from repo metadata
        """
        if not repos:
            return 0

        # ── Repo count score (0-25) ───────────────────────────────
        repo_count = len(repos)
        if repo_count >= 20:
            count_score = 25
        elif repo_count >= 10:
            count_score = 20
        elif repo_count >= 5:
            count_score = 15
        elif repo_count >= 2:
            count_score = 10
        else:
            count_score = 5

        # ── Average size score (0-25) ─────────────────────────────
        sizes = [r.get("size", 0) for r in repos]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        if avg_size >= 5000:
            size_score = 25
        elif avg_size >= 1000:
            size_score = 20
        elif avg_size >= 500:
            size_score = 15
        elif avg_size >= 100:
            size_score = 10
        else:
            size_score = 5

        # ── Description diversity (0-25) ──────────────────────────
        descriptions = [
            r.get("description", "") or ""
            for r in repos
            if r.get("description")
        ]
        topics = set()
        for repo in repos:
            for topic in repo.get("topics", []):
                topics.add(topic.lower())

        diversity_items = len(descriptions) + len(topics)
        if diversity_items >= 15:
            diversity_score = 25
        elif diversity_items >= 10:
            diversity_score = 20
        elif diversity_items >= 5:
            diversity_score = 15
        elif diversity_items >= 2:
            diversity_score = 10
        else:
            diversity_score = 5

        # ── Complexity indicators (0-25) ──────────────────────────
        has_stars = any(r.get("stargazers_count", 0) > 0 for r in repos)
        has_wiki = any(r.get("has_wiki", False) for r in repos)
        has_pages = any(r.get("has_pages", False) for r in repos)
        has_multiple_languages = len(set(
            r.get("language", "") for r in repos if r.get("language")
        )) >= 3

        complexity_score = 5  # base
        if has_stars:
            complexity_score += 5
        if has_wiki:
            complexity_score += 5
        if has_pages:
            complexity_score += 5
        if has_multiple_languages:
            complexity_score += 5
        complexity_score = min(25, complexity_score)

        total = count_score + size_score + diversity_score + complexity_score
        return min(100, max(0, total))

    # ── AI Usage Detection ────────────────────────────────────────

    def _detect_ai_usage(self, repos: List[dict]) -> str:
        """Estimate AI/ML usage level from repo metadata."""
        ai_keywords = {
            "machine-learning", "deep-learning", "ml", "ai",
            "tensorflow", "pytorch", "neural", "nlp", "llm",
            "transformer", "gpt", "openai", "langchain",
        }

        ai_count = 0
        for repo in repos:
            name = (repo.get("name", "") or "").lower()
            desc = (repo.get("description", "") or "").lower()
            topics = [t.lower() for t in repo.get("topics", [])]

            combined = f"{name} {desc} {' '.join(topics)}"
            if any(kw in combined for kw in ai_keywords):
                ai_count += 1

        if ai_count >= 3:
            return "High"
        elif ai_count >= 1:
            return "Medium"
        return "Low"

    # ── HTTP Request with Retry ───────────────────────────────────

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
    ) -> Optional[any]:
        """
        Make an HTTP request with exponential backoff retry.

        Returns None on 404 (user not found).
        Raises on persistent failures after MAX_RETRIES.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.request(
                    method, url, params=params, timeout=15
                )

                if resp.status_code == 404:
                    logger.warning("GitHub 404: %s", url)
                    return None

                if resp.status_code == 403:
                    # Rate limit hit
                    reset_time = resp.headers.get("X-RateLimit-Reset")
                    if reset_time:
                        wait = max(0, int(reset_time) - int(time.time()))
                        wait = min(wait, 60)  # Cap at 60s
                    else:
                        wait = RETRY_BASE_DELAY * (2 ** (attempt - 1))

                    logger.warning(
                        "GitHub rate limit hit, waiting %ds (attempt %d/%d)",
                        wait,
                        attempt,
                        MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.RequestException as e:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "GitHub request failed (attempt %d/%d): %s. Retrying in %.1fs",
                    attempt,
                    MAX_RETRIES,
                    str(e),
                    delay,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(delay)

        logger.error("GitHub request failed after %d retries: %s", MAX_RETRIES, url)
        return None

    # ── Username Parsing ──────────────────────────────────────────

    @staticmethod
    def parse_username(online_links: str) -> Optional[str]:
        """
        Extract GitHub username from an online_links string.

        Handles formats:
            - https://github.com/username
            - http://github.com/username
            - github.com/username
            - Comma-separated lists containing GitHub URLs
        """
        if not online_links:
            return None

        # Find GitHub URL in the links
        pattern = r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)"
        match = re.search(pattern, online_links, re.IGNORECASE)

        if match:
            username = match.group(1)
            # Filter out non-user paths
            excluded = {"login", "signup", "explore", "settings", "orgs"}
            if username.lower() not in excluded:
                return username

        return None

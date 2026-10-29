"""
VeriHire v2 - GitHub Evidence Collection Service
Uses GitHub GraphQL API to fetch public profile stats, owned non-fork repositories,
contributions, and merged external pull requests.
Stores compact normalized payloads without raw responses or personal data.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_USER_REGEX = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

GITHUB_GRAPHQL_QUERY = """
query($login: String!, $prQuery: String!) {
  user(login: $login) {
    createdAt
    followers {
      totalCount
    }
    repositories(
      first: 30
      ownerAffiliations: [OWNER]
      isFork: false
      orderBy: { field: PUSHED_AT, direction: DESC }
    ) {
      totalCount
      nodes {
        name
        stargazerCount
        forkCount
        primaryLanguage {
          name
        }
        pushedAt
        isArchived
        isFork
        readme: object(expression: "HEAD:README.md") {
          ... on Blob {
            byteSize
          }
        }
        readmeLower: object(expression: "HEAD:readme.md") {
          ... on Blob {
            byteSize
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
    }
  }
  search(query: $prQuery, type: ISSUE, first: 0) {
    issueCount
  }
  rateLimit {
    cost
    remaining
    resetAt
  }
}
"""


def parse_github_username(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses and validates a GitHub username from a link or raw string.
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

    if s.lower().startswith("github.com/"):
        s = s[len("github.com/") :]

    s = s.strip("/").lstrip("@")
    parts = [p for p in s.split("/") if p]
    if not parts:
        return None, "invalid_link"

    username = parts[0].strip()
    if not GITHUB_USER_REGEX.match(username):
        return None, "invalid_link"

    return username, None


def normalize_github_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts a compact, normalized payload from GitHub GraphQL data.
    Does NOT store raw responses or personal data (emails, names, bios, etc.).
    """
    user = data.get("user") or {}
    followers_count = (user.get("followers") or {}).get("totalCount", 0)
    repos_obj = user.get("repositories") or {}
    public_repos_count = repos_obj.get("totalCount", 0)
    repo_nodes: List[Dict[str, Any]] = repos_obj.get("nodes") or []

    total_stars = sum(r.get("stargazerCount", 0) for r in repo_nodes)
    total_forks = sum(r.get("forkCount", 0) for r in repo_nodes)

    cc = user.get("contributionsCollection") or {}
    commit_contributions = cc.get("totalCommitContributions", 0)
    pr_contributions = cc.get("totalPullRequestContributions", 0)
    review_contributions = cc.get("totalPullRequestReviewContributions", 0)
    restricted_contributions = cc.get("restrictedContributionsCount", 0)

    merged_external_prs = (data.get("search") or {}).get("issueCount", 0)

    # Language histogram across sampled repos
    languages: Dict[str, int] = {}
    for r in repo_nodes:
        lang_obj = r.get("primaryLanguage")
        if lang_obj and lang_obj.get("name"):
            name = lang_obj["name"]
            languages[name] = languages.get(name, 0) + 1

    # Top repos sorted by stars descending (up to 10)
    sorted_repos = sorted(repo_nodes, key=lambda x: x.get("stargazerCount", 0), reverse=True)[:10]
    top_repos = [
        {
            "name": r.get("name"),
            "stars": r.get("stargazerCount", 0),
            "forks": r.get("forkCount", 0),
            "language": (r.get("primaryLanguage") or {}).get("name") if r.get("primaryLanguage") else None,
            "pushed_at": r.get("pushedAt"),
            "is_archived": bool(r.get("isArchived", False)),
            "has_readme": bool(r.get("readme") or r.get("readmeLower")),
        }
        for r in sorted_repos
    ]

    flags = {
        "has_active_repos": any(not r.get("isArchived") for r in repo_nodes),
        "has_contributions": (commit_contributions + pr_contributions + review_contributions) > 0,
        "has_external_prs": merged_external_prs > 0,
    }

    return {
        "created_at": user.get("createdAt"),
        "followers_count": followers_count,
        "public_repos_count": public_repos_count,
        "owned_repos_sampled": len(repo_nodes),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "commit_contributions": commit_contributions,
        "pr_contributions": pr_contributions,
        "review_contributions": review_contributions,
        "restricted_contributions": restricted_contributions,
        "merged_external_prs": merged_external_prs,
        "language_histogram": languages,
        "top_repos": top_repos,
        "flags": flags,
    }


async def fetch_github_evidence(
    client: httpx.AsyncClient,
    username: str,
    token: Optional[str],
    rate_limit_remaining: Optional[int] = None,
    out_meta: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[str], Dict[str, Any], Optional[int]]:
    """
    Fetches GitHub evidence for a single user via GraphQL.
    Returns (status, reason, payload, remaining_rate_limit).
    Status is one of: 'verified', 'unverified', 'error'.
    """
    if not token:
        return "unverified", "no_token", {}, rate_limit_remaining

    if rate_limit_remaining is not None and rate_limit_remaining < 50:
        return "unverified", "rate_limited", {}, rate_limit_remaining

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "VeriHire-Evidence-Collector",
    }
    pr_query = f"author:{username} is:pr is:merged -user:{username}"
    payload_body = {
        "query": GITHUB_GRAPHQL_QUERY,
        "variables": {"login": username, "prQuery": pr_query},
    }

    max_retries = 2
    attempt = 0
    current_remaining = rate_limit_remaining

    while attempt <= max_retries:
        try:
            response = await client.post(
                GITHUB_GRAPHQL_URL,
                json=payload_body,
                headers=headers,
                timeout=10.0,
            )

            if out_meta is not None:
                out_meta["status_code"] = response.status_code

            # Check for secondary rate limit (HTTP 403 / 429) or server errors (502, 503, 504)
            is_secondary_rl = response.status_code in (403, 429) and (
                "retry-after" in response.headers
                or "secondary rate limit" in response.text.lower()
            )
            is_server_error = response.status_code in (502, 503, 504)

            if (is_secondary_rl or is_server_error) and attempt < max_retries:
                attempt += 1
                retry_after_str = response.headers.get("retry-after")
                if retry_after_str:
                    try:
                        wait_seconds = min(max(float(retry_after_str), 0.5), 30.0)
                    except ValueError:
                        wait_seconds = 1.0 * (attempt**1.5)
                else:
                    wait_seconds = 0.5 * (attempt**1.5)
                await asyncio.sleep(wait_seconds)
                continue

            if response.status_code != 200:
                short_code = f"http_{response.status_code}"
                if response.status_code in (403, 429) and is_secondary_rl:
                    short_code = "secondary_rate_limit"
                return "error", short_code, {}, current_remaining

            try:
                result_json = response.json()
            except Exception:
                return "error", "invalid_json", {}, current_remaining

            if not isinstance(result_json, dict):
                return "error", "invalid_response", {}, current_remaining

            data = result_json.get("data") or {}
            rate_limit_info = data.get("rateLimit") or {}
            if "remaining" in rate_limit_info and isinstance(rate_limit_info["remaining"], int):
                current_remaining = rate_limit_info["remaining"]
            if out_meta is not None:
                out_meta["cost"] = rate_limit_info.get("cost")
                out_meta["remaining"] = current_remaining

            user_data = data.get("user")
            errors = result_json.get("errors") or []

            # Check if user not found
            if user_data is None:
                # GitHub GraphQL returns null for user when login doesn't exist
                return "unverified", "not_found", {}, current_remaining

            if errors and not user_data:
                return "error", "graphql_error", {}, current_remaining

            normalized = normalize_github_payload(data)
            return "verified", None, normalized, current_remaining

        except httpx.TimeoutException:
            if attempt < max_retries:
                attempt += 1
                await asyncio.sleep(0.5 * attempt)
                continue
            return "error", "timeout", {}, current_remaining
        except httpx.RequestError:
            if attempt < max_retries:
                attempt += 1
                await asyncio.sleep(0.5 * attempt)
                continue
            return "error", "network_error", {}, current_remaining
        except Exception:
            return "error", "unexpected_error", {}, current_remaining

    return "error", "max_retries_exceeded", {}, current_remaining

"""
VeriHire v2 - Evidence Orchestration Service
Orchestrates evidence collection for top-ranked candidates of a job:
- GitHub evidence (GraphQL with concurrency semaphore)
- LeetCode evidence (unofficial GraphQL sequentially)
- Caching: reuses verified or not_found evidence < EVIDENCE_TTL_DAYS
- Time budget & rate limit enforcement
- Safe upserting of evidence rows
"""

import asyncio
from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session_factory
from app.models import Candidate, Evidence, Ranking
from app.services.evidence_github import (
    fetch_github_evidence,
    parse_github_username,
)
from app.services.evidence_leetcode import (
    fetch_leetcode_evidence,
    parse_leetcode_username,
)

logger = logging.getLogger(__name__)


def get_cached_evidence(
    db: Session,
    source: str,
    username: str,
    ttl_days: int,
) -> Optional[Evidence]:
    """
    Looks up a reusable verified or unverified(not_found) evidence row
    for the same (source, username) younger than ttl_days from ANY candidate.
    Errors and rate_limited results are never cached.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    stmt = (
        select(Evidence)
        .where(
            Evidence.source == source,
            Evidence.username == username,
            Evidence.fetched_at >= cutoff,
            or_(
                Evidence.status == "verified",
                and_(Evidence.status == "unverified", Evidence.reason == "not_found"),
            ),
        )
        .order_by(Evidence.fetched_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


async def _process_github_candidate(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    cand_id: uuid.UUID,
    raw_link: Optional[str],
    token: Optional[str],
    deadline: float,
    rate_limit_state: Dict[str, Any],
    ttl_days: int,
    session_factory: Any,
) -> Dict[str, Any]:
    """Processes GitHub evidence lookup for a single candidate."""
    now = datetime.now(timezone.utc)

    # 1. Budget check
    if time.monotonic() >= deadline:
        return {
            "candidate_id": cand_id,
            "source": "github",
            "username": None,
            "status": "unverified",
            "reason": "budget_exceeded",
            "payload": {},
            "fetched_at": now,
        }

    # 2. Username parsing
    username, parse_err = parse_github_username(raw_link)
    if parse_err:
        return {
            "candidate_id": cand_id,
            "source": "github",
            "username": username,
            "status": "unverified",
            "reason": parse_err,
            "payload": {},
            "fetched_at": now,
        }

    # 3. Token check
    if not token:
        return {
            "candidate_id": cand_id,
            "source": "github",
            "username": username,
            "status": "unverified",
            "reason": "no_token",
            "payload": {},
            "fetched_at": now,
        }

    # 4. Rate limit check
    if rate_limit_state.get("is_limited"):
        return {
            "candidate_id": cand_id,
            "source": "github",
            "username": username,
            "status": "unverified",
            "reason": "rate_limited",
            "payload": {},
            "fetched_at": now,
        }

    # 5. Cache check
    with session_factory() as db:
        cached = get_cached_evidence(db, "github", username, ttl_days)
        if cached:
            return {
                "candidate_id": cand_id,
                "source": "github",
                "username": username,
                "status": cached.status,
                "reason": cached.reason,
                "payload": cached.payload or {},
                "fetched_at": cached.fetched_at,
            }

    # 6. Fetch from GitHub GraphQL with concurrency limit
    async with semaphore:
        # Check budget again after waiting for semaphore
        if time.monotonic() >= deadline:
            return {
                "candidate_id": cand_id,
                "source": "github",
                "username": username,
                "status": "unverified",
                "reason": "budget_exceeded",
                "payload": {},
                "fetched_at": datetime.now(timezone.utc),
            }

        if rate_limit_state.get("is_limited"):
            return {
                "candidate_id": cand_id,
                "source": "github",
                "username": username,
                "status": "unverified",
                "reason": "rate_limited",
                "payload": {},
                "fetched_at": datetime.now(timezone.utc),
            }

        try:
            status, reason, payload, remaining = await fetch_github_evidence(
                client=client,
                username=username,
                token=token,
                rate_limit_remaining=rate_limit_state.get("remaining"),
            )
            if remaining is not None:
                rate_limit_state["remaining"] = remaining
                if remaining < 50:
                    rate_limit_state["is_limited"] = True

            return {
                "candidate_id": cand_id,
                "source": "github",
                "username": username,
                "status": status,
                "reason": reason,
                "payload": payload,
                "fetched_at": datetime.now(timezone.utc),
            }
        except Exception:
            logger.exception("Unexpected failure fetching GitHub evidence for candidate=%s", cand_id)
            return {
                "candidate_id": cand_id,
                "source": "github",
                "username": username,
                "status": "error",
                "reason": "fetch_exception",
                "payload": {},
                "fetched_at": datetime.now(timezone.utc),
            }


async def _process_leetcode_candidate(
    client: httpx.AsyncClient,
    cand_id: uuid.UUID,
    raw_link: Optional[str],
    deadline: float,
    ttl_days: int,
    session_factory: Any,
) -> Dict[str, Any]:
    """Processes LeetCode evidence lookup for a single candidate sequentially."""
    now = datetime.now(timezone.utc)

    # 1. Budget check
    if time.monotonic() >= deadline:
        return {
            "candidate_id": cand_id,
            "source": "leetcode",
            "username": None,
            "status": "unverified",
            "reason": "budget_exceeded",
            "payload": {},
            "fetched_at": now,
        }

    # 2. Username parsing
    username, parse_err = parse_leetcode_username(raw_link)
    if parse_err:
        return {
            "candidate_id": cand_id,
            "source": "leetcode",
            "username": username,
            "status": "unverified",
            "reason": parse_err,
            "payload": {},
            "fetched_at": now,
        }

    # 3. Cache check
    with session_factory() as db:
        cached = get_cached_evidence(db, "leetcode", username, ttl_days)
        if cached:
            return {
                "candidate_id": cand_id,
                "source": "leetcode",
                "username": username,
                "status": cached.status,
                "reason": cached.reason,
                "payload": cached.payload or {},
                "fetched_at": cached.fetched_at,
            }

    # 4. Fetch from LeetCode (sequential, rate limited <= 1 req/sec)
    try:
        status, reason, payload = await fetch_leetcode_evidence(
            client=client,
            username=username,
        )
        return {
            "candidate_id": cand_id,
            "source": "leetcode",
            "username": username,
            "status": status,
            "reason": reason,
            "payload": payload,
            "fetched_at": datetime.now(timezone.utc),
        }
    except Exception:
        logger.exception("Unexpected failure fetching LeetCode evidence for candidate=%s", cand_id)
        return {
            "candidate_id": cand_id,
            "source": "leetcode",
            "username": username,
            "status": "error",
            "reason": "fetch_exception",
            "payload": {},
            "fetched_at": datetime.now(timezone.utc),
        }


async def run_evidence_pipeline(job_id: uuid.UUID) -> None:
    """
    Main async worker function that runs evidence collection for a job.
    Fetches top N candidates by rank, runs GitHub & LeetCode lookups,
    and upserts evidence rows into the database.
    """
    settings = get_settings()
    session_factory = get_session_factory()

    # 1. Retrieve top N candidates from rankings
    with session_factory() as db:
        rankings_query = (
            select(Ranking, Candidate)
            .join(Candidate, Ranking.candidate_id == Candidate.id)
            .where(Ranking.job_id == job_id)
            .order_by(Ranking.rank.asc())
            .limit(settings.evidence_top_n)
        )
        ranked_candidates = db.execute(rankings_query).all()

    if not ranked_candidates:
        return

    deadline = time.monotonic() + settings.evidence_time_budget_seconds
    rate_limit_state: Dict[str, Any] = {"remaining": None, "is_limited": False}
    semaphore = asyncio.Semaphore(settings.evidence_concurrency)
    token = settings.raw_github_token

    collected_evidence: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        # A. GitHub Evidence Collection (concurrent with semaphore)
        gh_tasks = [
            _process_github_candidate(
                client=client,
                semaphore=semaphore,
                cand_id=c.id,
                raw_link=(c.links or {}).get("github"),
                token=token,
                deadline=deadline,
                rate_limit_state=rate_limit_state,
                ttl_days=settings.evidence_ttl_days,
                session_factory=session_factory,
            )
            for _, c in ranked_candidates
        ]
        gh_results = await asyncio.gather(*gh_tasks, return_exceptions=True)
        for cand_tuple, res in zip(ranked_candidates, gh_results):
            if isinstance(res, Exception):
                collected_evidence.append(
                    {
                        "candidate_id": cand_tuple[1].id,
                        "source": "github",
                        "username": None,
                        "status": "error",
                        "reason": "task_exception",
                        "payload": {},
                        "fetched_at": datetime.now(timezone.utc),
                    }
                )
            else:
                collected_evidence.append(res)

        # B. LeetCode Evidence Collection (sequential)
        for _, c in ranked_candidates:
            try:
                lc_res = await _process_leetcode_candidate(
                    client=client,
                    cand_id=c.id,
                    raw_link=(c.links or {}).get("leetcode"),
                    deadline=deadline,
                    ttl_days=settings.evidence_ttl_days,
                    session_factory=session_factory,
                )
                collected_evidence.append(lc_res)
            except Exception:
                logger.exception("Error collecting LeetCode evidence for candidate=%s", c.id)
                collected_evidence.append(
                    {
                        "candidate_id": c.id,
                        "source": "leetcode",
                        "username": None,
                        "status": "error",
                        "reason": "task_exception",
                        "payload": {},
                        "fetched_at": datetime.now(timezone.utc),
                    }
                )

    # 3. Persist evidence rows (upsert)
    with session_factory() as db:
        for item in collected_evidence:
            cand_id = item["candidate_id"]
            source = item["source"]
            existing = db.execute(
                select(Evidence).where(
                    Evidence.candidate_id == cand_id,
                    Evidence.source == source,
                )
            ).scalar_one_or_none()

            if existing:
                existing.username = item["username"]
                existing.status = item["status"]
                existing.reason = item["reason"]
                existing.payload = item["payload"]
                existing.fetched_at = item["fetched_at"]
            else:
                db.add(
                    Evidence(
                        candidate_id=cand_id,
                        source=source,
                        username=item["username"],
                        status=item["status"],
                        reason=item["reason"],
                        payload=item["payload"],
                        fetched_at=item["fetched_at"],
                    )
                )
        db.commit()


def collect_evidence_for_job(job_id: uuid.UUID) -> None:
    """Synchronous entry point that runs the async evidence pipeline."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In an already running event loop, create a task or run via thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(asyncio.run, run_evidence_pipeline(job_id)).result()
        else:
            loop.run_until_complete(run_evidence_pipeline(job_id))
    except RuntimeError:
        asyncio.run(run_evidence_pipeline(job_id))

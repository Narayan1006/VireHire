"""
VeriHire AI - Candidate Persistence Store

JSON-file based storage for ranked pipeline results.
Supports save/load, CRUD operations, and 90-day retention.

Requirements: 28.1, 28.2, 28.3, 28.4, 28.5
"""

import json
import os
import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models.candidate import CandidateOutput
from app.utils.logger import get_logger

logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
STORE_FILE = os.path.join(DATA_DIR, "candidates.json")
RETENTION_DAYS = 90


class CandidateStore:
    """JSON-file backed candidate store with in-memory index."""

    def __init__(self, store_path: str = STORE_FILE):
        self.store_path = store_path
        self._lock = threading.Lock()
        self._jobs: Dict[str, dict] = {}  # job_id -> {candidates, timestamp, jd}
        self._load()

    # ── Save / Load ───────────────────────────────────────────────

    def save_candidates(
        self,
        job_id: str,
        candidates: List[CandidateOutput],
        job_description: str = "",
    ) -> None:
        """Persist ranked results for a job."""
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "job_description": job_description,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "candidates": [c.model_dump(mode="json") for c in candidates],
            }
            self._flush()

        logger.info(
            "Saved %d candidates for job %s",
            len(candidates),
            job_id,
        )

    def load_candidates(
        self,
        job_id: str,
    ) -> Optional[List[CandidateOutput]]:
        """Load ranked results for a job. Returns None if not found."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return [CandidateOutput(**c) for c in job["candidates"]]

    def get_job_ids(self) -> List[str]:
        """Get all stored job IDs."""
        with self._lock:
            return list(self._jobs.keys())

    # ── CRUD ──────────────────────────────────────────────────────

    def get_candidate(
        self, job_id: str, candidate_id: str
    ) -> Optional[CandidateOutput]:
        """Get a single candidate by job_id and candidate_id."""
        candidates = self.load_candidates(job_id)
        if not candidates:
            return None
        for c in candidates:
            if c.id == candidate_id:
                return c
        return None

    def get_latest_job_id(self) -> Optional[str]:
        """Get the most recent job_id."""
        with self._lock:
            if not self._jobs:
                return None
            return max(
                self._jobs.keys(),
                key=lambda jid: self._jobs[jid]["timestamp"],
            )

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its candidates."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._flush()
                return True
            return False

    # ── Retention ─────────────────────────────────────────────────

    def enforce_retention(self) -> int:
        """Delete jobs older than RETENTION_DAYS. Returns count deleted."""
        now = datetime.now(timezone.utc)
        deleted = 0

        with self._lock:
            expired = []
            for job_id, job in self._jobs.items():
                try:
                    ts = datetime.fromisoformat(job["timestamp"])
                    age_days = (now - ts).days
                    if age_days > RETENTION_DAYS:
                        expired.append(job_id)
                except (ValueError, KeyError):
                    continue

            for job_id in expired:
                del self._jobs[job_id]
                deleted += 1

            if deleted:
                self._flush()

        if deleted:
            logger.info("Retention: deleted %d expired jobs", deleted)

        return deleted

    # ── Internal ──────────────────────────────────────────────────

    def _load(self) -> None:
        """Load from disk."""
        if not os.path.exists(self.store_path):
            return
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._jobs = {j["job_id"]: j for j in data.get("jobs", [])}
            logger.info("Loaded %d jobs from store", len(self._jobs))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load store: %s", e)
            self._jobs = {}

    def _flush(self) -> None:
        """Write to disk."""
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        data = {"jobs": list(self._jobs.values())}
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

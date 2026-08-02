"""
VeriHire AI - Candidate Persistence Store (PostgreSQL)

Supabase PostgreSQL-based storage for ranked pipeline results.
Supports save/load, CRUD operations, and 90-day retention.

Replaces JSON file storage with database persistence.
Maintains same API interface as CandidateStore for backward compatibility.

Requirements: 28.1, 28.2, 28.3, 28.4, 28.5
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from supabase import create_client, Client

from app.config import get_settings
from app.models.candidate import CandidateOutput
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CandidateStorePG:
    """PostgreSQL-backed candidate store using Supabase."""

    def __init__(self):
        settings = get_settings()
        
        if not settings.supabase_url:
            raise RuntimeError(
                "Supabase URL not configured. Set SUPABASE_URL in .env"
            )
        
        # Use service role key for backend operations (bypasses RLS)
        api_key = settings.supabase_service_role_key or settings.supabase_anon_key
        
        if not api_key:
            raise RuntimeError(
                "Supabase API key not configured. "
                "Set SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in .env"
            )
        
        self.client: Client = create_client(
            settings.supabase_url,
            api_key
        )
        logger.info("PostgreSQL candidate store initialized")

    # ── Save / Load ───────────────────────────────────────────────

    def save_candidates(
        self,
        job_id: str,
        candidates: List[CandidateOutput],
        job_description: str = "",
        user_id: Optional[str] = None,
    ) -> None:
        """
        Persist ranked results for a job.
        
        Args:
            job_id: 8-char hex job ID
            candidates: List of ranked candidates
            job_description: Job description text
            user_id: User ID from auth context (required for RLS)
        """
        if not user_id:
            raise ValueError("user_id is required for saving candidates")
        
        try:
            # 1. Insert or update job
            job_data = {
                "job_id": job_id,
                "user_id": user_id,
                "job_description": job_description,
            }
            
            # Upsert job (insert or update if exists)
            self.client.table("jobs").upsert(
                job_data,
                on_conflict="job_id"
            ).execute()
            
            # 2. Delete existing candidates for this job (if any)
            self.client.table("candidates").delete().eq(
                "job_id", job_id
            ).execute()
            
            # 3. Insert new candidates
            candidate_rows = []
            for c in candidates:
                row = {
                    "job_id": job_id,
                    "candidate_id": c.id,
                    "name": c.name,
                    "email": c.email,
                    "role": c.role,
                    "rank": c.rank,
                    "percentile": c.percentile,
                    "pr_score": c.pr_score,
                    "github_score": c.github_score,
                    "dsa_score": c.dsa_score,
                    "verdict": c.verdict,
                    "skills": [s.model_dump() for s in c.skills],
                    "github_evidence": c.github_evidence.model_dump(),
                    "leetcode": c.leetcode.model_dump(),
                    "codeforces": c.codeforces.model_dump() if c.codeforces else None,
                    "timeline": [t.model_dump() for t in c.timeline],
                    "risk_flags": [r.model_dump() for r in c.risk_flags],
                    "summary": c.summary,
                    "layer1_score": c.layer1_score,
                    "layer2_score": c.layer2_score,
                    "layer3_confidence": c.layer3_confidence,
                }
                candidate_rows.append(row)
            
            if candidate_rows:
                self.client.table("candidates").insert(candidate_rows).execute()
            
            logger.info(
                "Saved %d candidates for job %s (user: %s)",
                len(candidates),
                job_id,
                user_id,
            )
        
        except Exception as e:
            logger.error("Failed to save candidates: %s", e)
            raise

    def load_candidates(
        self,
        job_id: str,
    ) -> Optional[List[CandidateOutput]]:
        """
        Load ranked results for a job. Returns None if not found.
        
        RLS ensures users can only load their own jobs.
        """
        try:
            response = self.client.table("candidates").select("*").eq(
                "job_id", job_id
            ).order("rank").execute()
            
            if not response.data:
                return None
            
            candidates = []
            for row in response.data:
                # Reconstruct CandidateOutput from database row
                candidate = CandidateOutput(
                    id=row["candidate_id"],
                    rank=row["rank"],
                    name=row["name"],
                    email=row["email"],
                    role=row["role"],
                    percentile=row["percentile"],
                    pr_score=row["pr_score"],
                    github_score=row["github_score"],
                    dsa_score=row["dsa_score"],
                    verdict=row["verdict"],
                    skills=row["skills"],
                    github_evidence=row["github_evidence"],
                    leetcode=row["leetcode"],
                    codeforces=row["codeforces"],
                    timeline=row["timeline"],
                    risk_flags=row["risk_flags"],
                    summary=row["summary"],
                    layer1_score=row["layer1_score"],
                    layer2_score=row["layer2_score"],
                    layer3_confidence=row["layer3_confidence"],
                )
                candidates.append(candidate)
            
            return candidates
        
        except Exception as e:
            logger.error("Failed to load candidates for job %s: %s", job_id, e)
            return None

    def get_job_ids(self) -> List[str]:
        """
        Get all stored job IDs for the current user.
        
        RLS ensures only user's own jobs are returned.
        """
        try:
            response = self.client.table("jobs").select("job_id").order(
                "created_at", desc=True
            ).execute()
            
            return [row["job_id"] for row in response.data]
        
        except Exception as e:
            logger.error("Failed to get job IDs: %s", e)
            return []

    # ── CRUD ──────────────────────────────────────────────────────

    def get_candidate(
        self, job_id: str, candidate_id: str
    ) -> Optional[CandidateOutput]:
        """Get a single candidate by job_id and candidate_id."""
        try:
            response = self.client.table("candidates").select("*").eq(
                "job_id", job_id
            ).eq("candidate_id", candidate_id).execute()
            
            if not response.data:
                return None
            
            row = response.data[0]
            return CandidateOutput(
                id=row["candidate_id"],
                rank=row["rank"],
                name=row["name"],
                email=row["email"],
                role=row["role"],
                percentile=row["percentile"],
                pr_score=row["pr_score"],
                github_score=row["github_score"],
                dsa_score=row["dsa_score"],
                verdict=row["verdict"],
                skills=row["skills"],
                github_evidence=row["github_evidence"],
                leetcode=row["leetcode"],
                codeforces=row["codeforces"],
                timeline=row["timeline"],
                risk_flags=row["risk_flags"],
                summary=row["summary"],
                layer1_score=row["layer1_score"],
                layer2_score=row["layer2_score"],
                layer3_confidence=row["layer3_confidence"],
            )
        
        except Exception as e:
            logger.error(
                "Failed to get candidate %s for job %s: %s",
                candidate_id,
                job_id,
                e,
            )
            return None

    def get_latest_job_id(self) -> Optional[str]:
        """Get the most recent job_id for the current user."""
        try:
            response = self.client.table("jobs").select("job_id").order(
                "created_at", desc=True
            ).limit(1).execute()
            
            if not response.data:
                return None
            
            return response.data[0]["job_id"]
        
        except Exception as e:
            logger.error("Failed to get latest job ID: %s", e)
            return None

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job and its candidates.
        
        Cascade delete automatically removes candidates.
        RLS ensures only user's own jobs can be deleted.
        """
        try:
            response = self.client.table("jobs").delete().eq(
                "job_id", job_id
            ).execute()
            
            return len(response.data) > 0
        
        except Exception as e:
            logger.error("Failed to delete job %s: %s", job_id, e)
            return False

    # ── Retention ─────────────────────────────────────────────────

    def enforce_retention(self) -> int:
        """
        Delete jobs older than 90 days. Returns count deleted.
        
        Uses the delete_expired_jobs() PostgreSQL function.
        """
        try:
            response = self.client.rpc("delete_expired_jobs").execute()
            deleted = response.data if response.data else 0
            
            if deleted:
                logger.info("Retention: deleted %d expired jobs", deleted)
            
            return deleted
        
        except Exception as e:
            logger.error("Failed to enforce retention: %s", e)
            return 0

    # ── Additional Methods ────────────────────────────────────────

    def get_job_stats(self, job_id: str) -> Optional[Dict]:
        """
        Get job statistics (candidate count, verdict breakdown).
        
        Uses the get_job_with_stats() PostgreSQL function.
        """
        try:
            response = self.client.rpc(
                "get_job_with_stats",
                {"p_job_id": job_id}
            ).execute()
            
            if not response.data:
                return None
            
            return response.data[0]
        
        except Exception as e:
            logger.error("Failed to get job stats for %s: %s", job_id, e)
            return None

    def get_all_jobs(self) -> List[Dict]:
        """
        Get all jobs for the current user with metadata.
        
        Returns list of dicts with job_id, job_description, timestamp.
        """
        try:
            response = self.client.table("jobs").select(
                "job_id, job_description, created_at"
            ).order("created_at", desc=True).execute()
            
            return [
                {
                    "job_id": row["job_id"],
                    "job_description": row["job_description"],
                    "timestamp": row["created_at"],
                }
                for row in response.data
            ]
        
        except Exception as e:
            logger.error("Failed to get all jobs: %s", e)
            return []

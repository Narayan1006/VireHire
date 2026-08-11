"""
VeriHire AI - Candidate Persistence Store (Firestore)

Google Cloud Firestore-backed storage for ranked pipeline results.
Maintains backward compatibility with CandidateStorePG interface.
"""

import json
import os
from typing import Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import get_settings
from app.models.candidate import CandidateOutput
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CandidateStorePG:
    """Firestore-backed candidate store replacing PostgreSQL/Supabase."""

    def __init__(self):
        settings = get_settings()

        if not firebase_admin._apps:
            cred_json = getattr(settings, "firebase_credentials_json", "")
            cred_path = getattr(settings, "firebase_credentials_path", "")

            if cred_json and cred_json.strip():
                logger.info("Initializing Firebase Admin in Python from JSON env var")
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
            elif cred_path and os.path.exists(cred_path):
                logger.info("Initializing Firebase Admin in Python from path: %s", cred_path)
                cred = credentials.Certificate(cred_path)
            else:
                logger.info("Initializing Firebase Admin in Python using Application Default Credentials")
                cred = credentials.ApplicationDefault()

            firebase_admin.initialize_app(cred)

        self.db = firestore.client()
        logger.info("Firestore candidate store initialized")

    def save_candidates(
        self,
        job_id: str,
        candidates: List[CandidateOutput],
        job_description: str = "",
        user_id: Optional[str] = None,
    ) -> None:
        """Persist ranked candidates to Firestore document under jobs/{job_id}."""
        if not user_id:
            raise ValueError("user_id is required for saving candidates")

        try:
            job_ref = self.db.collection("jobs").document(job_id)
            job_ref.set(
                {
                    "job_id": job_id,
                    "user_id": user_id,
                    "job_description": job_description,
                    "created_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

            # Store candidates in subcollection jobs/{job_id}/candidates
            cand_coll = job_ref.collection("candidates")
            batch = self.db.batch()

            for c in candidates:
                cand_doc = cand_coll.document(c.id)
                cand_data = {
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
                batch.set(cand_doc, cand_data)

            batch.commit()
            logger.info("Saved %d candidates to Firestore for job %s", len(candidates), job_id)

        except Exception as e:
            logger.error("Failed to save candidates to Firestore: %s", e)
            raise

    def load_candidates(self, job_id: str) -> Optional[List[CandidateOutput]]:
        """Load candidates from Firestore collection jobs/{job_id}/candidates."""
        try:
            cand_ref = self.db.collection("jobs").document(job_id).collection("candidates")
            docs = cand_ref.order_by("rank").stream()

            candidates = []
            for doc in docs:
                data = doc.to_dict()
                candidates.append(
                    CandidateOutput(
                        id=data["candidate_id"],
                        rank=data["rank"],
                        name=data["name"],
                        email=data["email"],
                        role=data["role"],
                        percentile=data["percentile"],
                        pr_score=data["pr_score"],
                        github_score=data["github_score"],
                        dsa_score=data["dsa_score"],
                        verdict=data["verdict"],
                        skills=data["skills"],
                        github_evidence=data["github_evidence"],
                        leetcode=data["leetcode"],
                        codeforces=data["codeforces"],
                        timeline=data["timeline"],
                        risk_flags=data["risk_flags"],
                        summary=data["summary"],
                        layer1_score=data["layer1_score"],
                        layer2_score=data["layer2_score"],
                        layer3_confidence=data["layer3_confidence"],
                    )
                )
            return candidates if candidates else None

        except Exception as e:
            logger.error("Failed to load candidates from Firestore for job %s: %s", job_id, e)
            return None

    def get_job_ids(self) -> List[str]:
        """Get all stored job IDs."""
        try:
            jobs_ref = self.db.collection("jobs").order_by("created_at", direction=firestore.Query.DESCENDING)
            return [doc.id for doc in jobs_ref.stream()]
        except Exception as e:
            logger.error("Failed to get job IDs from Firestore: %s", e)
            return []

    def delete_job(self, job_id: str) -> bool:
        """Delete job document from Firestore."""
        try:
            self.db.collection("jobs").document(job_id).delete()
            return True
        except Exception as e:
            logger.error("Failed to delete job %s from Firestore: %s", job_id, e)
            return False

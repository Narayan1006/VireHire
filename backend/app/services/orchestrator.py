"""
VeriHire AI - Pipeline Orchestrator

Wires all 3 layers into a single execute_pipeline() call:

    CSV -> Layer 1 (Semantic Retrieval, top 200)
        -> Layer 2 (Evidence Verification + Scoring)
        -> Layer 3 (LLM Reasoning, top 50)
        -> Ranking Engine (Rank + Verdict)
        -> CandidateOutput[]

Handles layer failures gracefully with logging and partial results.

Requirements: 16.1, 16.2, 16.3, 16.4, 16.5
"""

import time
from typing import List, Optional

import pandas as pd

from app.config import Settings, get_settings
from app.models.candidate import CandidateOutput
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PipelineOrchestrator:
    """
    End-to-end ranking pipeline orchestrator.

    Executes the 3-layer AI pipeline:
        Layer 1: Semantic retrieval from ChromaDB
        Layer 2: Evidence extraction + mathematical scoring
        Layer 3: LLM explanation generation
        Final:   Score aggregation, ranking, verdicts
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def execute_pipeline(
        self,
        job_description: str,
        csv_path: Optional[str] = None,
        df: Optional[pd.DataFrame] = None,
        layer1_top_k: Optional[int] = None,
        layer2_top_k: Optional[int] = None,
        provider: Optional[str] = "groq",
        github_token: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
    ) -> List[CandidateOutput]:
        """
        Execute the complete 3-layer ranking pipeline.

        Args:
            job_description: The JD text to match candidates against.
            csv_path: Path to CSV on disk (local dev / bundled dataset).
            df: In-memory CSV data (production uploads — no disk).
            layer1_top_k: Candidates from Layer 1 (default: 200).
            layer2_top_k: Candidates from Layer 2 to Layer 3 (default: 50).
            provider: AI provider for Layer 1 and 3 (groq/ollama).
            github_token: User's GitHub token.
            groq_api_key: User's Groq API key.
            ollama_base_url: User's Ollama URL.

        Returns:
            Ranked list of CandidateOutput with verdicts.

        Raises:
            ValueError: If job_description is empty.
        """
        if not job_description or not job_description.strip():
            raise ValueError("Job description cannot be empty")

        if df is None and csv_path is None:
            csv_path = self.settings.csv_data_path
        layer1_top_k = layer1_top_k or self.settings.layer1_top_k
        layer2_top_k = layer2_top_k or self.settings.layer2_top_k

        t_pipeline_start = time.time()
        logger.info(
            "Pipeline started: L1_top_k=%d, L2_top_k=%d",
            layer1_top_k,
            layer2_top_k,
        )

        # ── Layer 1: Semantic Retrieval ───────────────────────────
        t_start = time.time()
        try:
            layer1_results = self._run_layer1(
                job_description, csv_path, df, layer1_top_k,
                provider=provider, groq_api_key=groq_api_key, ollama_base_url=ollama_base_url
            )
        except Exception as e:
            logger.error("Layer 1 failed: %s", str(e))
            raise RuntimeError(f"Layer 1 failed: {e}") from e

        logger.info(
            "Layer 1 complete: %d candidates in %.2fs",
            len(layer1_results),
            time.time() - t_start,
        )

        if not layer1_results:
            logger.warning("Layer 1 returned 0 candidates, pipeline aborted")
            return []

        # ── Layer 2: Evidence Verification ────────────────────────
        t_start = time.time()
        try:
            layer2_results = self._run_layer2(
                layer1_results, job_description,
                github_token=github_token, provider=provider, groq_api_key=groq_api_key, ollama_base_url=ollama_base_url
            )
        except Exception as e:
            logger.error("Layer 2 failed: %s", str(e))
            # Fallback: pass L1 results directly to L3 with zero scores
            layer2_results = self._layer2_fallback(layer1_results)

        logger.info(
            "Layer 2 complete: %d candidates in %.2fs",
            len(layer2_results),
            time.time() - t_start,
        )

        # ── Layer 3: LLM Reasoning ───────────────────────────────
        t_start = time.time()
        try:
            layer3_results = self._run_layer3(
                layer2_results, layer2_top_k,
                provider=provider, groq_api_key=groq_api_key, ollama_base_url=ollama_base_url
            )
        except Exception as e:
            logger.error("Layer 3 failed: %s", str(e))
            # Fallback: use L2 results with empty summaries
            layer3_results = self._layer3_fallback(
                layer2_results, layer2_top_k
            )

        logger.info(
            "Layer 3 complete: %d candidates in %.2fs",
            len(layer3_results),
            time.time() - t_start,
        )

        # ── Final: Ranking + Verdicts ─────────────────────────────
        t_start = time.time()
        from app.services.ranking_engine import RankingEngine

        ranker = RankingEngine(self.settings)
        final_results = ranker.rank_candidates(layer3_results)

        logger.info(
            "Ranking complete: %d candidates in %.2fs",
            len(final_results),
            time.time() - t_start,
        )

        elapsed = time.time() - t_pipeline_start
        logger.info(
            "Pipeline complete: %d ranked candidates in %.2fs",
            len(final_results),
            elapsed,
        )

        return final_results

    # ── Layer Implementations ─────────────────────────────────────

    def _run_layer1(
        self,
        job_description: str,
        csv_path: Optional[str],
        df: Optional[pd.DataFrame],
        top_k: int,
        provider: str = "groq",
        groq_api_key: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
    ) -> list:
        """Run Layer 1: CSV parsing + embedding + ChromaDB retrieval + LLM filter."""
        from app.services.layer1_rag import Layer1RAGFilter

        rag = Layer1RAGFilter()

        rag.ingest_candidates(csv_path=csv_path, df=df)

        # Retrieve top K by semantic similarity + optional LLM filter
        results = rag.retrieve_top_candidates(
            job_description=job_description,
            top_k=top_k,
            groq_api_key=groq_api_key or self.settings.groq_api_key,
            groq_model=self.settings.groq_model,
        )

        return results

    def _run_layer2(self, candidates: list, job_description: str = "", github_token: Optional[str] = None,
                    provider: str = "groq", groq_api_key: Optional[str] = None, ollama_base_url: Optional[str] = None) -> list:
        """Run Layer 2: Evidence extraction + math scoring + LLM analysis."""
        from app.services.layer2_evidence import EvidenceExtractor

        extractor = EvidenceExtractor(
            github_token=github_token or self.settings.github_token,
            parallel_workers=self.settings.parallel_workers,
            groq_api_key=groq_api_key or self.settings.groq_api_key,
            groq_model=self.settings.groq_model,
            job_description=job_description,
        )

        return extractor.process_candidates(candidates)

    def _run_layer3(self, scored_candidates: list, top_k: int, provider: str = "groq",
                    groq_api_key: Optional[str] = None, ollama_base_url: Optional[str] = None) -> list:
        """Run Layer 3: LLM explanation generation."""
        from app.services.layer3_llm import Layer3LLMReasoner

        reasoner = Layer3LLMReasoner(
            self.settings, 
            provider=provider, 
            groq_api_key=groq_api_key, 
            ollama_base_url=ollama_base_url
        )
        return reasoner.generate_explanations(
            scored_candidates, top_k=top_k
        )

    # ── Fallbacks ─────────────────────────────────────────────────

    def _layer2_fallback(self, layer1_results: list) -> list:
        """Create minimal ScoredCandidates when Layer 2 fails entirely."""
        from app.models.ranking import ScoredCandidate

        logger.warning(
            "Using Layer 2 fallback for %d candidates",
            len(layer1_results),
        )

        return [
            ScoredCandidate(
                candidate_id=c.candidate_id,
                name=c.name,
                email=c.email,
                role=c.role,
                skills=c.skills,
                online_links=c.online_links,
                timeline=c.timeline,
                layer1_score=c.similarity_score,
                github_score=0,
                dsa_score=0,
                consistency_score=0.5,
            )
            for c in layer1_results
        ]

    def _layer3_fallback(
        self, scored_candidates: list, top_k: int
    ) -> list:
        """Create CandidateWithExplanation with template summaries when L3 fails."""
        from app.models.ranking import CandidateWithExplanation

        logger.warning(
            "Using Layer 3 fallback for %d candidates",
            min(top_k, len(scored_candidates)),
        )

        # Sort by L2 score and take top K
        sorted_candidates = sorted(
            scored_candidates,
            key=lambda c: (
                c.github_score / 100 * 0.4
                + c.dsa_score / 100 * 0.4
                + c.consistency_score * 0.2
            ),
            reverse=True,
        )[:top_k]

        results = []
        for c in sorted_candidates:
            summary = (
                f"{c.name} is being evaluated for the {c.role} position. "
                f"GitHub score: {c.github_score}/100. "
                f"DSA score: {c.dsa_score}/100. "
                f"Consistency: {round(c.consistency_score * 100)}%."
            )
            results.append(
                CandidateWithExplanation(
                    candidate_id=c.candidate_id,
                    name=c.name,
                    email=c.email,
                    role=c.role,
                    skills=c.skills,
                    online_links=c.online_links,
                    timeline=c.timeline,
                    layer1_score=c.layer1_score,
                    github_score=c.github_score,
                    dsa_score=c.dsa_score,
                    consistency_score=c.consistency_score,
                    github_evidence=c.github_evidence,
                    leetcode_stats=c.leetcode_stats,
                    codeforces_stats=c.codeforces_stats,
                    skill_scores=c.skill_scores,
                    risk_flags=c.risk_flags,
                    summary=summary,
                    layer3_confidence=0.3,
                )
            )

        return results

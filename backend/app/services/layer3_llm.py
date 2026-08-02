"""
VeriHire AI - Layer 3: LLM Reasoning

Orchestrates explanation generation for the top-K scored candidates
using the Groq LLM client. Produces CandidateWithExplanation objects.

Pipeline:
    1. Select top 50 candidates by total Layer 2 score
    2. Generate LLM explanation for each (with fallback)
    3. Extract LLM confidence from the explanation
    4. Return CandidateWithExplanation objects

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import time
from typing import List, Optional

from app.config import Settings, get_settings
from app.integrations.groq_client import GroqClient
from app.models.ranking import CandidateWithExplanation, ScoredCandidate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Layer3LLMReasoner:
    """
    Layer 3: LLM Reasoning engine.

    Generates human-readable hiring explanations for the top
    candidates using Groq API (Llama 3).
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.groq_client = GroqClient(
            api_key=self.settings.groq_api_key,
            model=self.settings.groq_model,
            base_url=self.settings.groq_base_url,
            max_tokens=self.settings.groq_max_tokens,
        )

    def generate_explanations(
        self,
        scored_candidates: List[ScoredCandidate],
        top_k: int = 50,
    ) -> List[CandidateWithExplanation]:
        """
        Generate LLM explanations for the top-K candidates.

        Steps:
            1. Sort candidates by combined Layer 2 score (descending)
            2. Select top_k candidates
            3. Generate explanation for each via Groq API
            4. Build CandidateWithExplanation objects

        Preconditions:
            - scored_candidates is non-empty
            - top_k is positive integer <= 50

        Postconditions:
            - Returns exactly min(top_k, len(scored_candidates)) results
            - All explanations are non-empty strings
            - API errors handled with fallback explanations

        Args:
            scored_candidates: List of ScoredCandidate from Layer 2.
            top_k: Maximum number of candidates to process.

        Returns:
            List of CandidateWithExplanation objects.
        """
        t_start = time.time()
        logger.info(
            "Layer 3 started: generating explanations for top %d of %d candidates",
            top_k,
            len(scored_candidates),
        )

        # Step 1: Sort by combined score (github + dsa + consistency)
        sorted_candidates = sorted(
            scored_candidates,
            key=lambda c: (
                c.github_score / 100 * 0.4
                + c.dsa_score / 100 * 0.4
                + c.consistency_score * 0.2
            ),
            reverse=True,
        )

        # Step 2: Select top K
        selected = sorted_candidates[:top_k]

        # Step 3: Generate explanations sequentially
        # (Groq has rate limits, sequential is safer)
        results: List[CandidateWithExplanation] = []

        for i, candidate in enumerate(selected, 1):
            logger.info(
                "Generating explanation %d/%d: %s",
                i,
                len(selected),
                candidate.name,
            )

            # Generate explanation via Groq
            summary = self.groq_client.generate_explanation(candidate)

            # Estimate LLM confidence from the explanation
            confidence = self._estimate_confidence(candidate, summary)

            # Build CandidateWithExplanation
            result = CandidateWithExplanation(
                candidate_id=candidate.candidate_id,
                name=candidate.name,
                email=candidate.email,
                role=candidate.role,
                skills=candidate.skills,
                online_links=candidate.online_links,
                timeline=candidate.timeline,
                layer1_score=candidate.layer1_score,
                github_score=candidate.github_score,
                dsa_score=candidate.dsa_score,
                consistency_score=candidate.consistency_score,
                github_evidence=candidate.github_evidence,
                leetcode_stats=candidate.leetcode_stats,
                codeforces_stats=candidate.codeforces_stats,
                skill_scores=candidate.skill_scores,
                risk_flags=candidate.risk_flags,
                summary=summary,
                layer3_confidence=confidence,
            )

            results.append(result)

        elapsed = time.time() - t_start
        logger.info(
            "Layer 3 complete: %d explanations in %.2fs (%.2fs/candidate)",
            len(results),
            elapsed,
            elapsed / len(selected) if selected else 0,
        )

        return results

    # ── Confidence Estimation ─────────────────────────────────────

    def _estimate_confidence(
        self,
        candidate: ScoredCandidate,
        summary: str,
    ) -> float:
        """
        Estimate LLM confidence based on evidence availability and
        explanation quality.

        Formula:
            - Base confidence from evidence coverage (0.0-0.6)
            - Bonus from explanation quality (0.0-0.4)

        Returns:
            Float between 0.0 and 1.0.
        """
        # Evidence coverage: each verified platform adds 0.2
        coverage = 0.0
        if candidate.github_evidence.verified:
            coverage += 0.2
        if candidate.leetcode_stats.verified:
            coverage += 0.2
        if candidate.codeforces_stats and candidate.codeforces_stats.verified:
            coverage += 0.2

        # Explanation quality: word count and keyword presence
        word_count = len(summary.split())
        quality = 0.0

        # Word count bonus (100-300 words is ideal)
        if 100 <= word_count <= 300:
            quality += 0.2
        elif 50 <= word_count:
            quality += 0.1

        # Contains recommendation keywords
        summary_lower = summary.lower()
        if any(kw in summary_lower for kw in ["hire", "review", "reject"]):
            quality += 0.1

        # References specific evidence
        if any(
            kw in summary_lower
            for kw in ["github", "leetcode", "codeforces", "repository", "rating"]
        ):
            quality += 0.1

        confidence = min(1.0, max(0.0, coverage + quality))
        return round(confidence, 2)

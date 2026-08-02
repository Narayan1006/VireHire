"""
VeriHire AI - Ranking Engine

Aggregates scores from all 3 layers, calculates final rankings,
assigns verdicts, and produces CandidateOutput objects.

Components:
  - ScoreAggregator: Weighted average across layers + PR score
  - RankingEngine: Sort, rank, percentile calculation
  - VerdictEngine: Threshold-based HIRE / REVIEW / REJECT

Requirements: 13.1-13.5, 14.1-14.5, 15.1-15.5
"""

from typing import List

from app.config import Settings, get_settings
from app.models.candidate import CandidateOutput
from app.models.ranking import CandidateWithExplanation, RankedCandidate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScoreAggregator:
    """
    Aggregate scores from all pipeline layers.

    Weights:
        Layer 1 (semantic similarity): 20%
        Layer 2 (evidence verification): 60%
        Layer 3 (LLM confidence): 20%

    PR Score:
        GitHub: 40%
        DSA: 40%
        Consistency: 20%
    """

    def __init__(self, settings: Settings = None):
        settings = settings or get_settings()
        self.weight_layer1 = settings.weight_layer1   # 0.2
        self.weight_layer2 = settings.weight_layer2   # 0.6
        self.weight_layer3 = settings.weight_layer3   # 0.2
        self.weight_github = settings.weight_github   # 0.4
        self.weight_dsa = settings.weight_dsa         # 0.4
        self.weight_consistency = settings.weight_consistency  # 0.2

    def aggregate_scores(self, candidate: CandidateWithExplanation) -> float:
        """
        Calculate final aggregated score (0.0-1.0).

        Formula:
            layer2_score = (github/100 * 0.4) + (dsa/100 * 0.4) + (consistency * 0.2)
            final = layer1 * 0.2 + layer2 * 0.6 + layer3 * 0.2

        Postconditions:
            - Returns float between 0.0 and 1.0
            - Deterministic
        """
        # Layer 2 composite
        layer2_score = (
            (candidate.github_score / 100.0) * self.weight_github
            + (candidate.dsa_score / 100.0) * self.weight_dsa
            + candidate.consistency_score * self.weight_consistency
        )

        # Weighted aggregate
        final = (
            candidate.layer1_score * self.weight_layer1
            + layer2_score * self.weight_layer2
            + candidate.layer3_confidence * self.weight_layer3
        )

        return round(max(0.0, min(1.0, final)), 4)

    def calculate_pr_score(
        self,
        github_score: int,
        dsa_score: int,
        consistency: float,
    ) -> int:
        """
        Calculate PR score (0-100).

        Formula:
            PR = github * 0.4 + dsa * 0.4 + consistency * 100 * 0.2

        Postconditions:
            - Returns integer between 0 and 100
        """
        pr = (
            github_score * self.weight_github
            + dsa_score * self.weight_dsa
            + consistency * 100 * self.weight_consistency
        )
        return max(0, min(100, round(pr)))


class VerdictEngine:
    """
    Assign hiring verdicts based on PR score thresholds.

    Thresholds (configurable):
        PR >= 80: HIRE
        PR >= 60: REVIEW
        PR <  60: REJECT
    """

    def __init__(self, settings: Settings = None):
        settings = settings or get_settings()
        self.hire_threshold = settings.verdict_hire_threshold    # 80
        self.review_threshold = settings.verdict_review_threshold  # 60

    def assign_verdict(self, pr_score: int) -> str:
        """
        Assign verdict based on PR score.

        Postconditions:
            - Returns one of: "HIRE", "REVIEW", "REJECT"
            - Deterministic (same score -> same verdict)
        """
        if pr_score >= self.hire_threshold:
            return "HIRE"
        elif pr_score >= self.review_threshold:
            return "REVIEW"
        else:
            return "REJECT"


class RankingEngine:
    """
    Calculate rankings, percentiles, and verdicts.

    Orchestrates ScoreAggregator and VerdictEngine to produce
    the final CandidateOutput list.
    """

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.aggregator = ScoreAggregator(self.settings)
        self.verdict_engine = VerdictEngine(self.settings)

    def rank_candidates(
        self,
        candidates: List[CandidateWithExplanation],
    ) -> List[CandidateOutput]:
        """
        Produce final ranked output from Layer 3 results.

        Steps:
            1. Aggregate scores (final_score, pr_score)
            2. Sort by final_score descending
            3. Assign ranks (1-indexed) and percentiles
            4. Assign verdicts based on PR score
            5. Build CandidateOutput objects

        Preconditions:
            - candidates is non-empty

        Postconditions:
            - Returns list sorted by rank ascending
            - All ranks are unique and sequential
            - All percentiles are 0-100
            - All verdicts are HIRE, REVIEW, or REJECT
        """
        if not candidates:
            return []

        logger.info("Ranking %d candidates", len(candidates))

        # Step 1: Compute scores
        scored = []
        for c in candidates:
            final_score = self.aggregator.aggregate_scores(c)
            pr_score = self.aggregator.calculate_pr_score(
                c.github_score, c.dsa_score, c.consistency_score
            )
            scored.append((c, final_score, pr_score))

        # Step 2: Sort by final_score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Step 3: Assign ranks and percentiles
        total = len(scored)
        results: List[CandidateOutput] = []

        for i, (c, final_score, pr_score) in enumerate(scored):
            rank = i + 1
            percentile = self.calculate_percentile(rank, total)
            verdict = self.verdict_engine.assign_verdict(pr_score)

            # Layer 2 composite for output
            layer2_score = (
                (c.github_score / 100.0) * self.aggregator.weight_github
                + (c.dsa_score / 100.0) * self.aggregator.weight_dsa
                + c.consistency_score * self.aggregator.weight_consistency
            )

            output = CandidateOutput(
                id=c.candidate_id,
                rank=rank,
                name=c.name,
                email=c.email,
                role=c.role,
                percentile=percentile,
                pr_score=pr_score,
                github_score=c.github_score,
                dsa_score=c.dsa_score,
                verdict=verdict,
                skills=c.skill_scores,
                github_evidence=c.github_evidence,
                leetcode=c.leetcode_stats,
                codeforces=c.codeforces_stats,
                timeline=c.timeline,
                risk_flags=c.risk_flags,
                summary=c.summary,
                layer1_score=c.layer1_score,
                layer2_score=round(layer2_score, 4),
                layer3_confidence=c.layer3_confidence,
            )

            results.append(output)

        # Log verdict distribution
        verdicts = [r.verdict for r in results]
        logger.info(
            "Ranking complete: %d HIRE, %d REVIEW, %d REJECT",
            verdicts.count("HIRE"),
            verdicts.count("REVIEW"),
            verdicts.count("REJECT"),
        )

        return results

    @staticmethod
    def calculate_percentile(rank: int, total: int) -> int:
        """
        Calculate percentile from rank and total count.

        Formula: ((total - rank + 1) / total) * 100

        Postconditions:
            - Returns integer 0-100
        """
        if total == 0:
            return 0
        pct = ((total - rank + 1) / total) * 100
        return max(0, min(100, round(pct)))

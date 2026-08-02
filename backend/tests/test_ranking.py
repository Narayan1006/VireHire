"""Unit tests for ranking engine and verdict assignment."""

import pytest

from app.models.candidate import SkillConfidence
from app.models.evidence import GitHubEvidence, LanguageDistribution, LeetCodeStats
from app.models.ranking import CandidateWithExplanation
from app.services.ranking_engine import (
    RankingEngine,
    ScoreAggregator,
    VerdictEngine,
)


# ── ScoreAggregator ───────────────────────────────────────────────


class TestScoreAggregator:
    def setup_method(self):
        self.agg = ScoreAggregator()

    def test_pr_score_formula(self):
        # PR = github*0.4 + dsa*0.4 + consistency*100*0.2
        assert self.agg.calculate_pr_score(80, 70, 0.9) == 78  # 32+28+18
        assert self.agg.calculate_pr_score(100, 100, 1.0) == 100
        assert self.agg.calculate_pr_score(0, 0, 0.0) == 0
        assert self.agg.calculate_pr_score(50, 50, 0.5) == 50  # 20+20+10

    def test_pr_score_clamped(self):
        assert self.agg.calculate_pr_score(100, 100, 1.0) == 100
        assert self.agg.calculate_pr_score(0, 0, 0.0) == 0

    def test_aggregate_scores(self):
        candidate = CandidateWithExplanation(
            candidate_id="c1", name="Test", email="t@t.com", role="Eng",
            layer1_score=0.8, github_score=80, dsa_score=60,
            consistency_score=0.9,
            github_evidence=GitHubEvidence(verified=False),
            leetcode_stats=LeetCodeStats(verified=False),
            summary="Test", layer3_confidence=0.7,
        )
        score = self.agg.aggregate_scores(candidate)
        assert 0.0 <= score <= 1.0

    def test_aggregate_deterministic(self):
        candidate = CandidateWithExplanation(
            candidate_id="c1", name="Test", email="t@t.com", role="Eng",
            layer1_score=0.5, github_score=50, dsa_score=50,
            consistency_score=0.5,
            github_evidence=GitHubEvidence(verified=False),
            leetcode_stats=LeetCodeStats(verified=False),
            summary="Test", layer3_confidence=0.5,
        )
        s1 = self.agg.aggregate_scores(candidate)
        s2 = self.agg.aggregate_scores(candidate)
        assert s1 == s2


# ── VerdictEngine ─────────────────────────────────────────────────


class TestVerdictEngine:
    def setup_method(self):
        self.engine = VerdictEngine()

    def test_hire_threshold(self):
        assert self.engine.assign_verdict(100) == "HIRE"
        assert self.engine.assign_verdict(80) == "HIRE"

    def test_review_threshold(self):
        assert self.engine.assign_verdict(79) == "REVIEW"
        assert self.engine.assign_verdict(60) == "REVIEW"

    def test_reject_threshold(self):
        assert self.engine.assign_verdict(59) == "REJECT"
        assert self.engine.assign_verdict(0) == "REJECT"

    def test_deterministic(self):
        assert self.engine.assign_verdict(75) == self.engine.assign_verdict(75)


# ── RankingEngine ─────────────────────────────────────────────────


class TestRankingEngine:
    def setup_method(self):
        self.engine = RankingEngine()

    def _make_candidate(self, name, gh, dsa, con, l1=0.5, l3=0.5):
        return CandidateWithExplanation(
            candidate_id=name.lower(), name=name, email=f"{name.lower()}@t.com",
            role="Eng", layer1_score=l1, github_score=gh, dsa_score=dsa,
            consistency_score=con,
            github_evidence=GitHubEvidence(verified=False),
            leetcode_stats=LeetCodeStats(verified=False),
            summary=f"Summary for {name}", layer3_confidence=l3,
        )

    def test_ranking_order(self):
        candidates = [
            self._make_candidate("Weak", 10, 10, 0.2),
            self._make_candidate("Strong", 90, 85, 0.95),
            self._make_candidate("Average", 50, 50, 0.5),
        ]
        results = self.engine.rank_candidates(candidates)
        assert results[0].name == "Strong"
        assert results[1].name == "Average"
        assert results[2].name == "Weak"

    def test_sequential_ranks(self):
        candidates = [
            self._make_candidate("A", 80, 80, 0.8),
            self._make_candidate("B", 60, 60, 0.6),
        ]
        results = self.engine.rank_candidates(candidates)
        assert [r.rank for r in results] == [1, 2]

    def test_unique_ranks(self):
        candidates = [self._make_candidate(f"C{i}", 50, 50, 0.5) for i in range(5)]
        results = self.engine.rank_candidates(candidates)
        ranks = [r.rank for r in results]
        assert len(ranks) == len(set(ranks))

    def test_percentiles(self):
        candidates = [self._make_candidate(f"C{i}", 50 + i * 10, 50, 0.5) for i in range(4)]
        results = self.engine.rank_candidates(candidates)
        assert results[0].percentile == 100
        assert results[-1].percentile == 25

    def test_empty_list(self):
        assert self.engine.rank_candidates([]) == []

    def test_output_fields(self):
        candidates = [self._make_candidate("Test", 80, 70, 0.9)]
        results = self.engine.rank_candidates(candidates)
        r = results[0]
        assert r.id == "test"
        assert r.name == "Test"
        assert r.verdict in ("HIRE", "REVIEW", "REJECT")
        assert 0 <= r.pr_score <= 100
        assert 0 <= r.percentile <= 100
        assert r.summary == "Summary for Test"

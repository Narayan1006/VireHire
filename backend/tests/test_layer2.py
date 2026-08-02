"""Unit tests for Layer 2 scoring and consistency checking."""

import pytest

from app.models.candidate import RiskFlag, SkillConfidence
from app.models.evidence import (
    CodeforcesStats,
    GitHubEvidence,
    LanguageDistribution,
    LeetCodeStats,
)
from app.services.layer2_evidence import (
    ConsistencyChecker,
    MathematicalScorer,
    parse_online_links,
)


# ── MathematicalScorer ────────────────────────────────────────────


class TestMathematicalScorer:
    """Tests for deterministic scoring formulas."""

    def setup_method(self):
        self.scorer = MathematicalScorer()

    # GitHub score

    def test_github_score_strong(self):
        evidence = GitHubEvidence(
            verified=True,
            username="strong",
            repo_count=50,
            languages=[
                LanguageDistribution(name="Python", percentage=40),
                LanguageDistribution(name="JavaScript", percentage=30),
                LanguageDistribution(name="TypeScript", percentage=20),
                LanguageDistribution(name="Go", percentage=10),
            ],
            architecture_score=100,
            last_active="2026-05-30",
        )
        score = self.scorer.calculate_github_score(evidence)
        assert 70 <= score <= 100

    def test_github_score_unverified(self):
        evidence = GitHubEvidence(verified=False)
        assert self.scorer.calculate_github_score(evidence) == 0

    def test_github_score_zero_repos(self):
        evidence = GitHubEvidence(
            verified=True, username="empty", repo_count=0,
            languages=[], architecture_score=0, last_active="Unknown",
        )
        assert self.scorer.calculate_github_score(evidence) == 0

    def test_github_score_deterministic(self):
        evidence = GitHubEvidence(
            verified=True, username="x", repo_count=10,
            languages=[LanguageDistribution(name="Python", percentage=100)],
            architecture_score=50, last_active="2026-05-30",
        )
        s1 = self.scorer.calculate_github_score(evidence)
        s2 = self.scorer.calculate_github_score(evidence)
        assert s1 == s2

    # DSA score

    def test_dsa_both_platforms(self):
        lc = LeetCodeStats(
            verified=True, username="x", rating=2500,
            problems_solved=400, consistency=80, easy=100, medium=200, hard=100,
        )
        cf = CodeforcesStats(
            verified=True, username="x", rating=2000,
            max_rating=2200, rank="candidate master", contests_participated=40,
        )
        score = self.scorer.calculate_dsa_score(lc, cf)
        assert 60 <= score <= 100

    def test_dsa_leetcode_only(self):
        lc = LeetCodeStats(
            verified=True, username="x", rating=2500,
            problems_solved=400, consistency=80, easy=100, medium=200, hard=100,
        )
        score = self.scorer.calculate_dsa_score(lc, None)
        assert score > 0

    def test_dsa_neither(self):
        lc = LeetCodeStats(verified=False)
        assert self.scorer.calculate_dsa_score(lc, None) == 0

    # Skill scores

    def test_skill_scores_verified(self):
        evidence = GitHubEvidence(
            verified=True, username="x", repo_count=10,
            languages=[LanguageDistribution(name="Python", percentage=60)],
            architecture_score=50, last_active="2026-05-30",
        )
        scores = self.scorer.calculate_skill_scores(evidence, ["Python"])
        assert len(scores) == 1
        assert scores[0].name == "Python"
        assert scores[0].verified == 100  # 60% * 2 = 120, capped at 100

    def test_skill_scores_empty(self):
        evidence = GitHubEvidence(verified=True, username="x", repo_count=0,
                                  languages=[], architecture_score=0)
        scores = self.scorer.calculate_skill_scores(evidence, [])
        assert scores == []


# ── ConsistencyChecker ────────────────────────────────────────────


class TestConsistencyChecker:
    """Tests for skill consistency and risk flag generation."""

    def setup_method(self):
        self.checker = ConsistencyChecker()

    def test_no_flags_for_unverified(self):
        evidence = GitHubEvidence(verified=False)
        flags = self.checker.check_skill_consistency(["Python"], evidence)
        assert flags == []

    def test_flags_for_skill_gap(self):
        evidence = GitHubEvidence(
            verified=True, username="x", repo_count=10,
            languages=[LanguageDistribution(name="JavaScript", percentage=90)],
            architecture_score=50,
        )
        flags = self.checker.check_skill_consistency(
            ["Python", "TypeScript"], evidence
        )
        # Python has 0% on GitHub -> high gap
        python_flags = [f for f in flags if "Python" in f.label]
        assert len(python_flags) == 1
        assert python_flags[0].severity == "high"

    def test_unique_flag_ids(self):
        evidence = GitHubEvidence(
            verified=True, username="x", repo_count=10,
            languages=[LanguageDistribution(name="Go", percentage=100)],
            architecture_score=50,
        )
        flags = self.checker.check_skill_consistency(
            ["Python", "Java", "Ruby"], evidence
        )
        ids = [f.id for f in flags]
        assert len(ids) == len(set(ids))

    def test_consistency_score_neutral(self):
        score = self.checker.calculate_consistency_score({}, {})
        assert score == 0.5

    def test_consistency_score_close(self):
        claimed = {"github": 80.0}
        verified = {"github": 75.0}
        score = self.checker.calculate_consistency_score(claimed, verified)
        assert score >= 0.9


# ── Link Parsing ──────────────────────────────────────────────────


class TestParseOnlineLinks:
    def test_github_and_leetcode(self):
        links = parse_online_links(
            "https://github.com/alice, https://leetcode.com/alice"
        )
        assert links == {"github": "alice", "leetcode": "alice"}

    def test_all_three_platforms(self):
        links = parse_online_links(
            "https://github.com/a, https://leetcode.com/b, https://codeforces.com/profile/c"
        )
        assert links == {"github": "a", "leetcode": "b", "codeforces": "c"}

    def test_empty_string(self):
        assert parse_online_links("") == {}

    def test_no_matching_links(self):
        assert parse_online_links("https://example.com") == {}

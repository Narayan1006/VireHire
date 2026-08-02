"""
VeriHire AI - Candidate Data Models

Pydantic models for candidate data throughout the pipeline:
- CandidateInput: Raw CSV data
- SkillConfidence, TimelineEntry, RiskFlag: Sub-models
- CandidateOutput: Final ranked candidate with all enrichments
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ── Sub-models ────────────────────────────────────────────────────


class SkillConfidence(BaseModel):
    """Skill with claimed vs verified scores."""

    name: str
    claimed: int = Field(ge=0, le=100, description="Claimed proficiency from resume (0-100)")
    verified: int = Field(ge=0, le=100, description="Verified proficiency from evidence (0-100)")


class TimelineEntry(BaseModel):
    """Experience or education timeline entry."""

    id: str
    type: str = Field(description='Entry type: "experience" or "education"')
    title: str
    organization: str
    period: str
    description: Optional[str] = None


class RiskFlag(BaseModel):
    """Inconsistency flag between claimed and verified data."""

    id: str
    severity: str = Field(description='Severity level: "low", "medium", or "high"')
    label: str
    description: str


# ── Input Model ───────────────────────────────────────────────────


class CandidateInput(BaseModel):
    """Raw candidate data from Kaggle CSV."""

    id: str
    name: str
    email: str
    role: str
    matched_score: float = Field(default=0.0, description="Original CSV matching score")
    online_links: str = Field(default="", description="Comma-separated URLs (GitHub, LeetCode, etc.)")
    skills: str = Field(default="", description="Comma-separated skill names")
    positions: str = Field(default="", description="JSON string of positions held")
    responsibilities: str = Field(default="", description="Free-text responsibilities")

    model_config = {"extra": "allow"}


# ── Output Model ──────────────────────────────────────────────────


class CandidateOutput(BaseModel):
    """Final ranked candidate with all enrichments from the 3-layer pipeline."""

    # Identity
    id: str
    rank: int = Field(ge=1, description="Unique sequential rank starting from 1")
    name: str
    email: str
    role: str

    # Scores
    percentile: int = Field(ge=0, le=100, description="Percentile score (0-100)")
    pr_score: int = Field(ge=0, le=100, description="Overall PR score (0-100)")
    github_score: int = Field(ge=0, le=100, description="GitHub verification score (0-100)")
    dsa_score: int = Field(ge=0, le=100, description="DSA score from LeetCode/Codeforces (0-100)")

    # Verdict
    verdict: str = Field(description='Hiring verdict: "HIRE", "REVIEW", or "REJECT"')

    # Enrichments
    skills: List[SkillConfidence] = Field(default_factory=list)
    github_evidence: "GitHubEvidence"
    leetcode: "LeetCodeStats"
    codeforces: Optional["CodeforcesStats"] = None
    timeline: List[TimelineEntry] = Field(default_factory=list)
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    summary: str = Field(default="", description="LLM-generated explanation (100-300 words)")

    # Layer scores
    layer1_score: float = Field(ge=0.0, le=1.0, description="Semantic similarity score")
    layer2_score: float = Field(ge=0.0, le=1.0, description="Evidence verification score")
    layer3_confidence: float = Field(ge=0.0, le=1.0, description="LLM confidence score")


# Deferred import resolution for forward references
from app.models.evidence import CodeforcesStats, GitHubEvidence, LeetCodeStats  # noqa: E402

CandidateOutput.model_rebuild()

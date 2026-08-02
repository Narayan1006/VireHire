"""
VeriHire AI - Ranking Pipeline Data Models

Intermediate models used between pipeline layers:
- ParsedResume: Output of resume parser
- TextChunk: Output of text chunker
- ChromaDBMetadata / ChromaDBDocument: Vector store schemas
- CandidateMatch: Layer 1 output
- VerifiedCandidate: Layer 2 input (evidence attached)
- ScoredCandidate: Layer 2 output (scores calculated)
- CandidateWithExplanation: Layer 3 output
- RankedCandidate: Final ranked output before verdict
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.candidate import (
    CandidateInput,
    RiskFlag,
    SkillConfidence,
    TimelineEntry,
)
from app.models.evidence import CodeforcesStats, GitHubEvidence, LeetCodeStats


# ── Layer 1 Models ────────────────────────────────────────────────


class ParsedResume(BaseModel):
    """Structured resume data after parsing."""

    candidate_id: str
    name: str
    email: str
    role: str
    skills: List[str] = Field(default_factory=list, description="Deduplicated skill names")
    online_links: str = Field(default="", description="Raw comma-separated URLs")
    matched_score: float = Field(default=0.0)
    text: str = Field(default="", description="Full resume text for chunking")
    timeline: List[TimelineEntry] = Field(default_factory=list)


class TextChunk(BaseModel):
    """A single text chunk from a resume for embedding."""

    candidate_id: str
    chunk_index: int = Field(ge=0, description="Sequential chunk index starting from 0")
    chunk_type: str = Field(description='Chunk type: "summary", "experience", "skills", or "education"')
    text: str = Field(description="Chunk text content (100-500 tokens)")


class ChromaDBMetadata(BaseModel):
    """Metadata stored alongside each vector in ChromaDB."""

    candidate_id: str
    name: str
    email: str
    role: str
    skills: str = Field(default="", description="Comma-separated skills")
    chunk_index: int = Field(ge=0)
    chunk_type: str
    matched_score: float = Field(default=0.0)


class ChromaDBDocument(BaseModel):
    """Complete document structure for ChromaDB insertion."""

    id: str = Field(description='Document ID: f"{candidate_id}_chunk_{chunk_index}"')
    embedding: List[float] = Field(description="384-dimensional embedding vector")
    document: str = Field(description="Text chunk content")
    metadata: ChromaDBMetadata


# ── Layer 1 → Layer 2 Handoff ─────────────────────────────────────


class CandidateMatch(BaseModel):
    """Layer 1 output: candidate with semantic similarity score."""

    candidate_id: str
    name: str
    email: str
    role: str
    skills: List[str] = Field(default_factory=list)
    online_links: str = Field(default="")
    matched_score: float = Field(default=0.0)
    similarity_score: float = Field(ge=0.0, le=1.0, description="Cosine similarity to job description")
    timeline: List[TimelineEntry] = Field(default_factory=list)


# ── Layer 2 Models ────────────────────────────────────────────────


class VerifiedCandidate(BaseModel):
    """Candidate with evidence data attached (before scoring)."""

    candidate: CandidateMatch
    github_evidence: GitHubEvidence = Field(default_factory=GitHubEvidence)
    leetcode_stats: LeetCodeStats = Field(default_factory=LeetCodeStats)
    codeforces_stats: Optional[CodeforcesStats] = None


class ScoredCandidate(BaseModel):
    """Candidate with all Layer 2 scores calculated."""

    # Identity (from CandidateMatch)
    candidate_id: str
    name: str
    email: str
    role: str
    skills: List[str] = Field(default_factory=list)
    online_links: str = Field(default="")
    timeline: List[TimelineEntry] = Field(default_factory=list)

    # Layer 1 score
    layer1_score: float = Field(ge=0.0, le=1.0, description="Semantic similarity score")

    # Layer 2 scores
    github_score: int = Field(ge=0, le=100, description="GitHub verification score (0-100)")
    dsa_score: int = Field(ge=0, le=100, description="DSA score (0-100)")
    consistency_score: float = Field(ge=0.0, le=1.0, description="Claim vs evidence consistency (0.0-1.0)")

    # Evidence data
    github_evidence: GitHubEvidence = Field(default_factory=GitHubEvidence)
    leetcode_stats: LeetCodeStats = Field(default_factory=LeetCodeStats)
    codeforces_stats: Optional[CodeforcesStats] = None

    # Enrichments
    skill_scores: List[SkillConfidence] = Field(default_factory=list)
    risk_flags: List[RiskFlag] = Field(default_factory=list)

    # LLM analysis (optional, populated when Groq is available)
    llm_analysis: Optional[Dict[str, int]] = Field(
        default=None,
        description="Raw LLM scores: {technical_depth, role_fit, evidence_strength}",
    )


# ── Layer 3 Models ────────────────────────────────────────────────


class CandidateWithExplanation(BaseModel):
    """Candidate with LLM-generated explanation (Layer 3 output)."""

    # Carry forward all ScoredCandidate fields
    candidate_id: str
    name: str
    email: str
    role: str
    skills: List[str] = Field(default_factory=list)
    online_links: str = Field(default="")
    timeline: List[TimelineEntry] = Field(default_factory=list)

    # Layer scores
    layer1_score: float = Field(ge=0.0, le=1.0)
    github_score: int = Field(ge=0, le=100)
    dsa_score: int = Field(ge=0, le=100)
    consistency_score: float = Field(ge=0.0, le=1.0)

    # Evidence
    github_evidence: GitHubEvidence = Field(default_factory=GitHubEvidence)
    leetcode_stats: LeetCodeStats = Field(default_factory=LeetCodeStats)
    codeforces_stats: Optional[CodeforcesStats] = None

    # Enrichments
    skill_scores: List[SkillConfidence] = Field(default_factory=list)
    risk_flags: List[RiskFlag] = Field(default_factory=list)

    # Layer 3 output
    summary: str = Field(default="", description="LLM-generated explanation (100-300 words)")
    layer3_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="LLM confidence score")


# ── Ranking Output ────────────────────────────────────────────────


class RankedCandidate(BaseModel):
    """Candidate with final rank and aggregated scores (before verdict)."""

    # Identity
    candidate_id: str
    name: str
    email: str
    role: str

    # Ranks and scores
    rank: int = Field(ge=1)
    percentile: int = Field(ge=0, le=100)
    pr_score: int = Field(ge=0, le=100, description="Overall PR score (0-100)")
    final_score: float = Field(ge=0.0, le=1.0, description="Weighted aggregated score")

    # Layer scores
    layer1_score: float = Field(ge=0.0, le=1.0)
    layer2_score: float = Field(ge=0.0, le=1.0)
    layer3_confidence: float = Field(ge=0.0, le=1.0)
    github_score: int = Field(ge=0, le=100)
    dsa_score: int = Field(ge=0, le=100)
    consistency_score: float = Field(ge=0.0, le=1.0)

    # Evidence
    github_evidence: GitHubEvidence = Field(default_factory=GitHubEvidence)
    leetcode_stats: LeetCodeStats = Field(default_factory=LeetCodeStats)
    codeforces_stats: Optional[CodeforcesStats] = None

    # Enrichments
    skills: List[str] = Field(default_factory=list)
    skill_scores: List[SkillConfidence] = Field(default_factory=list)
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    timeline: List[TimelineEntry] = Field(default_factory=list)
    summary: str = Field(default="")

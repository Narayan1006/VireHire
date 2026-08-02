"""
VeriHire AI - Evidence Data Models

Pydantic models for Layer 2 evidence verification data:
- LanguageDistribution: GitHub language breakdown
- GitHubEvidence: GitHub verification data
- LeetCodeStats: LeetCode verification data
- CodeforcesStats: Codeforces verification data
"""

from typing import List

from pydantic import BaseModel, Field


class LanguageDistribution(BaseModel):
    """Single language in a GitHub language breakdown."""

    name: str
    percentage: int = Field(ge=0, le=100, description="Language percentage (0-100)")


class GitHubEvidence(BaseModel):
    """GitHub verification data extracted via API."""

    username: str = Field(default="")
    repo_count: int = Field(default=0, ge=0, description="Total public repositories")
    languages: List[LanguageDistribution] = Field(default_factory=list)
    architecture_score: int = Field(default=0, ge=0, le=100, description="Architecture complexity score (0-100)")
    ai_usage_level: str = Field(default="Low", description='AI usage level: "Low", "Medium", or "High"')
    last_active: str = Field(default="Unknown", description="Human-readable last activity date")
    verified: bool = Field(default=False, description="Whether GitHub data was successfully verified")


class LeetCodeStats(BaseModel):
    """LeetCode verification data extracted via GraphQL API."""

    username: str = Field(default="")
    rating: int = Field(default=0, ge=0, description="LeetCode contest rating")
    problems_solved: int = Field(default=0, ge=0, description="Total problems solved")
    consistency: int = Field(default=0, ge=0, le=100, description="Consistency score (0-100)")
    easy: int = Field(default=0, ge=0, description="Easy problems solved")
    medium: int = Field(default=0, ge=0, description="Medium problems solved")
    hard: int = Field(default=0, ge=0, description="Hard problems solved")
    verified: bool = Field(default=False, description="Whether LeetCode data was successfully verified")


class CodeforcesStats(BaseModel):
    """Codeforces verification data extracted via REST API."""

    username: str = Field(default="")
    rating: int = Field(default=0, ge=0, description="Current Codeforces rating")
    max_rating: int = Field(default=0, ge=0, description="Maximum achieved rating")
    rank: str = Field(default="unrated", description="Codeforces rank title")
    contests_participated: int = Field(default=0, ge=0, description="Number of contests participated")
    verified: bool = Field(default=False, description="Whether Codeforces data was successfully verified")

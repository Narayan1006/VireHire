"""
VeriHire v2 - Application Configuration
"""

from functools import lru_cache
from typing import List

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    jwt_secret: str

    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    version: str = "2.0.0"
    env: str = "development"
    trust_proxy_headers: bool = False

    max_upload_size_bytes: int = 5 * 1024 * 1024  # 5 MB
    max_csv_rows: int = 1000
    max_resume_length: int = 20000
    retrieval_top_k: int = 200

    github_token: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    explanation_top_m: int = 20
    evidence_top_n: int = 50
    evidence_ttl_days: int = 7
    evidence_time_budget_seconds: int = 90
    evidence_concurrency: int = 5

    # Provisional scoring parameters (M3B default weights, caps, thresholds; tuned in M4)
    scoring_weight_external_collaboration: float = 0.25
    scoring_weight_repo_impact: float = 0.15
    scoring_weight_sustained_activity: float = 0.25
    scoring_weight_breadth: float = 0.10
    scoring_weight_skill_overlap: float = 0.15
    scoring_weight_leetcode: float = 0.10

    scoring_cap_stars: int = 500
    scoring_cap_external_prs: int = 20
    scoring_cap_commits: int = 1500
    scoring_cap_repos: int = 30
    scoring_cap_reviews: int = 50
    scoring_cap_forks: int = 100
    scoring_cap_followers: int = 100
    scoring_cap_leetcode_hard: int = 50
    scoring_cap_leetcode_medium: int = 150
    scoring_cap_leetcode_total: int = 300
    scoring_cap_leetcode_rating: float = 2400.0
    scoring_cap_account_age_days: int = 1825

    scoring_max_evidence_weight: float = 0.4
    scoring_min_confidence: float = 0.2
    scoring_strong_threshold: float = 0.75


    @field_validator("max_csv_rows")
    @classmethod
    def validate_max_csv_rows(cls, v: int) -> int:
        return min(max(1, v), 5000)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "DATABASE_URL is required and cannot be empty. "
                "Provide a valid postgresql+psycopg:// connection string."
            )
        val = v.strip()
        if val.startswith("postgres://"):
            val = "postgresql+psycopg://" + val[len("postgres://"):]
        elif val.startswith("postgresql://") and not val.startswith("postgresql+"):
            val = "postgresql+psycopg://" + val[len("postgresql://"):]
        return val

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "JWT_SECRET is required and cannot be empty."
            )
        val = v.strip()
        if len(val) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters long."
            )
        return val

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def raw_github_token(self) -> str | None:
        """Returns the unmasked GitHub token string or None without logging or leaking it."""
        if self.github_token is None:
            return None
        val = self.github_token.get_secret_value().strip()
        return val if val else None

    @property
    def raw_groq_api_key(self) -> str | None:
        """Returns the unmasked Groq API key or None without logging or leaking it."""
        if self.groq_api_key is None:
            return None
        val = self.groq_api_key.get_secret_value().strip()
        return val if val else None

    def __repr__(self) -> str:
        return f"<Settings env={self.env!r} version={self.version!r}>"



@lru_cache
def get_settings() -> Settings:
    return Settings()

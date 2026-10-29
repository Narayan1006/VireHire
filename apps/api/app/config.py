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
    evidence_top_n: int = 50
    evidence_ttl_days: int = 7
    evidence_time_budget_seconds: int = 90
    evidence_concurrency: int = 5


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
        return v.strip()

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

    def __repr__(self) -> str:
        return f"<Settings env={self.env!r} version={self.version!r}>"



@lru_cache
def get_settings() -> Settings:
    return Settings()

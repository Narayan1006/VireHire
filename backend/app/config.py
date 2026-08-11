"""
VeriHire AI - Configuration Management

Centralized configuration using Pydantic BaseSettings.
Loads values from environment variables and .env file.
"""

import os
from typing import List

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ────────────────────────────────────────────────
    app_name: str = "VeriHire AI"
    app_version: str = "1.0.2"
    debug: bool = Field(default=False, description="Enable debug mode")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    log_level: str = Field(default="INFO", description="Logging level")

    # ── API Keys (loaded from env – never hardcoded) ───────────────
    groq_api_key: str = Field(
        default="",
        description="Groq API key for Layer 3 LLM reasoning",
    )
    github_token: str = Field(
        default="",
        description="GitHub personal access token for Layer 2 evidence",
    )

    # ── ChromaDB ───────────────────────────────────────────────────
    chromadb_path: str = Field(
        default="./data/chroma_db",
        description="Path to ChromaDB persistence directory",
    )
    chromadb_collection_name: str = Field(
        default="candidates",
        description="ChromaDB collection name",
    )

    # ── CORS ───────────────────────────────────────────────────────
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:5174,https://vire-hire.vercel.app",
        description="Comma-separated allowed CORS origins",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [
            origin.strip().strip("'\"").rstrip("/") 
            for origin in self.cors_origins.split(",") 
            if origin.strip()
        ]

    # ── Firebase / Firestore ──────────────────────────────────────
    auth_enabled: bool = Field(
        default=True,
        description="Set to false to disable auth (dev/test only)."
    )
    firebase_credentials_json: str = Field(
        default="",
        description="Raw JSON string of Firebase service account key"
    )
    firebase_credentials_path: str = Field(
        default="",
        description="Path to Firebase serviceAccountKey.json"
    )
    jwt_secret: str = Field(
        default="",
        description="Spring Boot JWT secret for HS256 verification (min 32 chars)"
    )

    # ── Data Paths ─────────────────────────────────────────────────
    csv_data_path: str = Field(
        default="./data/resume_data_for_ranking.csv",
        description="Path to the Kaggle CSV data file",
    )

    # ── Embedding Model ────────────────────────────────────────────
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers model for embeddings",
    )
    embedding_dimension: int = Field(
        default=384,
        description="Dimension of embedding vectors",
    )
    embedding_batch_size: int = Field(
        default=64,
        description="Batch size for embedding generation",
    )

    # ── LLM Configuration ─────────────────────────────────────────
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model identifier",
    )
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq API base URL",
    )
    groq_max_tokens: int = Field(
        default=500,
        description="Maximum tokens for LLM response",
    )

    # ── Pipeline Defaults ──────────────────────────────────────────
    layer1_top_k: int = Field(
        default=200,
        description="Number of candidates passed from Layer 1 to Layer 2",
    )
    layer2_top_k: int = Field(
        default=50,
        description="Number of candidates passed from Layer 2 to Layer 3",
    )
    parallel_workers: int = Field(
        default=15,
        description="Thread pool workers for parallel API calls",
    )

    # ── Cache ──────────────────────────────────────────────────────
    cache_ttl_hours: int = Field(
        default=24,
        description="Cache TTL in hours for API responses",
    )

    # ── Rate Limiting ──────────────────────────────────────────────
    rate_limit_rank: str = Field(
        default="5/hour",
        description="Rate limit for POST /api/rank",
    )
    rate_limit_candidates: str = Field(
        default="100/minute",
        description="Rate limit for GET /api/candidates",
    )
    rate_limit_export: str = Field(
        default="10/hour",
        description="Rate limit for GET /api/export",
    )

    # ── Verdict Thresholds ─────────────────────────────────────────
    verdict_hire_threshold: int = Field(
        default=80,
        description="Minimum PR score for HIRE verdict",
    )
    verdict_review_threshold: int = Field(
        default=60,
        description="Minimum PR score for REVIEW verdict",
    )

    # ── Score Weights ──────────────────────────────────────────────
    weight_layer1: float = Field(default=0.2, description="Layer 1 weight in final score")
    weight_layer2: float = Field(default=0.6, description="Layer 2 weight in final score")
    weight_layer3: float = Field(default=0.2, description="Layer 3 weight in final score")

    weight_github: float = Field(default=0.4, description="GitHub weight in PR score")
    weight_dsa: float = Field(default=0.4, description="DSA weight in PR score")
    weight_consistency: float = Field(default=0.2, description="Consistency weight in PR score")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


from functools import lru_cache


@lru_cache()
def get_settings() -> Settings:
    """
    Factory function to create and return a Settings instance.

    Uses environment variables and .env file for configuration.
    Cached via @lru_cache to avoid reading env vars on every call.
    """
    return Settings()


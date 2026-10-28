"""
Tests for configuration and fail-fast environment validation
"""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_fail_when_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("JWT_SECRET", "super-secret-jwt-key-min-32-chars")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "DATABASE_URL" in str(exc_info.value) or "database_url" in str(exc_info.value)


def test_settings_fail_when_database_url_empty(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    monkeypatch.setenv("JWT_SECRET", "super-secret-jwt-key-min-32-chars")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "DATABASE_URL" in str(exc_info.value) or "database_url" in str(exc_info.value)


def test_settings_fail_when_jwt_secret_missing(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "JWT_SECRET" in str(exc_info.value) or "jwt_secret" in str(exc_info.value)


def test_settings_fail_when_jwt_secret_empty(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "JWT_SECRET" in str(exc_info.value) or "jwt_secret" in str(exc_info.value)


def test_settings_fail_when_jwt_secret_too_short(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "short-secret")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "at least 32 characters" in str(exc_info.value)


def test_settings_success_with_valid_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "super-secret-jwt-key-min-32-chars")
    monkeypatch.setenv("CORS_ORIGINS", "https://virehire.web.app,http://localhost:5173")

    s = Settings(_env_file=None)
    assert s.database_url == "postgresql+psycopg://user:pass@localhost:5432/db"
    assert s.jwt_secret == "super-secret-jwt-key-min-32-chars"
    assert s.cors_origin_list == ["https://virehire.web.app", "http://localhost:5173"]


def test_max_csv_rows_default_and_ceiling(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "super-secret-jwt-key-min-32-chars")

    # Default is 1000
    s_default = Settings(_env_file=None)
    assert s_default.max_csv_rows == 1000

    # Overridden via env
    monkeypatch.setenv("MAX_CSV_ROWS", "2500")
    s_custom = Settings(_env_file=None)
    assert s_custom.max_csv_rows == 2500

    # Hard ceiling caps at 5000
    monkeypatch.setenv("MAX_CSV_ROWS", "99999")
    s_capped = Settings(_env_file=None)
    assert s_capped.max_csv_rows == 5000


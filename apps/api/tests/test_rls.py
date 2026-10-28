"""
Test that all public schema tables have Row Level Security (RLS) enabled
"""

import os
import urllib.parse
import pytest
from sqlalchemy import text

from app.database import build_engine

LOCAL_DOCKER_DB_URL = "postgresql+psycopg://postgres:password@localhost:5433/verihire"


@pytest.mark.postgres
def test_public_tables_have_rls_enabled():
    """
    Verifies every table in public schema has relrowsecurity = true.
    Uses TEST_DATABASE_URL (or DATABASE_URL for compatibility).
    """
    db_url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") or LOCAL_DOCKER_DB_URL
    db_url = db_url.strip()

    parsed = urllib.parse.urlparse(db_url)
    assert "supabase" not in (parsed.hostname or "").lower(), "TEST_DATABASE_URL must never point to Supabase"

    is_ci = os.environ.get("CI", "").strip().lower() in ("true", "1") or os.environ.get("REQUIRE_POSTGRES", "").strip().lower() in ("true", "1")

    try:
        engine = build_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    except Exception as exc:
        if is_ci:
            pytest.fail(f"PostgreSQL database unreachable in CI ({type(exc).__name__}: {exc}). Skipping is forbidden.")
        pytest.skip(f"Postgres database unreachable ({type(exc).__name__}); skipping live RLS check.")


        # Query all ordinary tables ('r') in the public schema, excluding alembic_version
        query = text("""
            SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND c.relname NOT IN ('alembic_version');
        """)
        rows = conn.execute(query).fetchall()
        if not rows:
            pytest.skip("No user tables found in public schema to evaluate.")

        unsecured_tables = [r.table_name for r in rows if not r.rls_enabled]
        assert not unsecured_tables, (
            f"Security violation: Tables in public schema without RLS enabled: {unsecured_tables}"
        )

"""
Postgres-only test for migrations and Row Level Security (RLS) enforcement.
Runs against the local Docker pgvector database.
"""

import os
import urllib.parse
from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text

from app.database import build_engine

LOCAL_DOCKER_DB_URL = "postgresql+psycopg://postgres:password@localhost:5433/verihire"


@pytest.mark.postgres
def test_postgres_migrations_and_rls_on_local_docker():
    """
    Runs migrations against local Docker Postgres and verifies that
    all user tables have Row Level Security (RLS) enabled.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL", LOCAL_DOCKER_DB_URL).strip()

    # Safety assertion
    parsed = urllib.parse.urlparse(test_db_url)
    assert "supabase" not in (parsed.hostname or "").lower(), "TEST_DATABASE_URL must never point to Supabase"

    is_ci = os.environ.get("CI", "").strip().lower() in ("true", "1") or os.environ.get("REQUIRE_POSTGRES", "").strip().lower() in ("true", "1")
    try:
        engine = build_engine(test_db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    except Exception as exc:
        if is_ci:
            pytest.fail(f"PostgreSQL database unreachable in CI ({type(exc).__name__}: {exc}). Skipping is forbidden.")
        pytest.skip(f"Local Docker Postgres unreachable ({type(exc).__name__}); skipping live test.")


    # Apply all migrations to local Docker database
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    command.upgrade(alembic_cfg, "head")

    with engine.connect() as conn:
        # Check all tables in public schema have RLS enabled
        query = text("""
            SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND c.relname NOT IN ('alembic_version');
        """)
        rows = {r.table_name: r.rls_enabled for r in conn.execute(query).fetchall()}

        assert "users" in rows, "users table missing from public schema"
        assert "jobs" in rows, "jobs table missing from public schema"
        assert "candidates" in rows, "candidates table missing from public schema"
        assert "rankings" in rows, "rankings table missing from public schema"
        assert "evidence" in rows, "evidence table missing from public schema"
        assert rows["users"] is True, "RLS is not enabled on users table"
        assert rows["jobs"] is True, "RLS is not enabled on jobs table"
        assert rows["candidates"] is True, "RLS is not enabled on candidates table"
        assert rows["rankings"] is True, "RLS is not enabled on rankings table"
        assert rows["evidence"] is True, "RLS is not enabled on evidence table"


        # Verify no table in public lacks RLS
        unsecured = [t for t, rls in rows.items() if not rls]
        assert not unsecured, f"Tables missing RLS: {unsecured}"

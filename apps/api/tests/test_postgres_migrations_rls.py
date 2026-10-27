"""
Postgres-only test for migrations and Row Level Security (RLS) enforcement.
Skipped unless TEST_DATABASE_URL is set.
"""

import os
import pytest
from sqlalchemy import create_engine, text


def test_postgres_migrations_and_rls_on_users_and_jobs():
    """
    Runs against a real PostgreSQL instance specified by TEST_DATABASE_URL.
    Verifies that Alembic migrations produce users and jobs tables with RLS enabled.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url or not test_db_url.strip():
        pytest.skip("TEST_DATABASE_URL is unset; skipping live Postgres migration and RLS verification.")

    engine = create_engine(
        test_db_url.strip(),
        connect_args={"prepare_threshold": None},
    )

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

        # Check RLS on users and jobs tables
        query = text("""
            SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND c.relname IN ('users', 'jobs');
        """)
        rows = {r.table_name: r.rls_enabled for r in conn.execute(query).fetchall()}

        assert "users" in rows, "users table missing from public schema"
        assert "jobs" in rows, "jobs table missing from public schema"
        assert rows["users"] is True, "RLS is not enabled on users table"
        assert rows["jobs"] is True, "RLS is not enabled on jobs table"

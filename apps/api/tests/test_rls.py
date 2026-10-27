"""
Test that all public schema tables have Row Level Security (RLS) enabled
"""

import os
import pytest
from sqlalchemy import create_engine, text


def test_public_tables_have_rls_enabled():
    """
    Verifies every table in public schema has relrowsecurity = true.
    Skips if DATABASE_URL is unset.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or not db_url.strip():
        pytest.skip("DATABASE_URL is unset; skipping live RLS check.")

    engine = create_engine(
        db_url,
        connect_args={"prepare_threshold": None},
    )
    with engine.connect() as conn:
        # Check if database responds
        conn.execute(text("SELECT 1"))

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

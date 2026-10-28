"""Create candidates and rankings tables with RLS and search index

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27 21:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensure pgvector extension exists and is in search_path
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("SET search_path TO public, extensions;")

    # 1. Create candidates table
    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("resume_text", sa.Text(), nullable=False),
        sa.Column(
            "links",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(name,'') || ' ' || coalesce(resume_text,''))",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_candidates_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candidates"),
    )

    # 2. Indexes for candidates
    op.create_index("ix_candidates_job_id", "candidates", ["job_id"])
    op.create_index(
        "ix_candidates_search_tsv",
        "candidates",
        ["search_tsv"],
        postgresql_using="gin",
    )
    op.create_index(
        "uq_candidates_job_id_email",
        "candidates",
        ["job_id", sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )

    # 3. Create rankings table
    op.create_table(
        "rankings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("retrieval_score", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_rankings_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_rankings_candidate_id_candidates",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rankings"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_rankings_job_candidate"),
    )
    op.create_index("ix_rankings_job_id", "rankings", ["job_id"])

    # 4. Enable Row Level Security (RLS) on both tables with no default policies
    op.execute("ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE rankings ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_table("rankings")
    op.drop_index("uq_candidates_job_id_email", table_name="candidates")
    op.drop_index("ix_candidates_search_tsv", table_name="candidates")
    op.drop_index("ix_candidates_job_id", table_name="candidates")
    op.drop_table("candidates")

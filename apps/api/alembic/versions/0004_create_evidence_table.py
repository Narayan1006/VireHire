"""Create evidence table with RLS and caching indexes

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-29 10:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evidence table
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_evidence_candidate_id_candidates",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence"),
        sa.CheckConstraint(
            "source IN ('github', 'leetcode')",
            name="ck_evidence_source",
        ),
        sa.CheckConstraint(
            "status IN ('verified', 'unverified', 'error')",
            name="ck_evidence_status",
        ),
        sa.UniqueConstraint("candidate_id", "source", name="uq_evidence_candidate_source"),
    )

    # 2. Create performance indexes
    op.create_index("ix_evidence_candidate_id", "evidence", ["candidate_id"])
    op.create_index(
        "ix_evidence_source_username_fetched_at",
        "evidence",
        ["source", "username", "fetched_at"],
    )

    # 3. Enable Row Level Security (RLS) with no default policies
    op.execute("ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_index("ix_evidence_source_username_fetched_at", table_name="evidence")
    op.drop_index("ix_evidence_candidate_id", table_name="evidence")
    op.drop_table("evidence")

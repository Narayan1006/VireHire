"""Create jobs table with RLS and owner index

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26 22:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_jobs_owner_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.CheckConstraint(
            "status IN ('draft', 'processing', 'done', 'failed')",
            name="ck_jobs_status",
        ),
    )
    op.create_index(
        "ix_jobs_owner_id_created_at",
        "jobs",
        ["owner_id", sa.text("created_at DESC")],
    )

    # Enable Row Level Security (RLS) on jobs table with no default policies
    op.execute("ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_index("ix_jobs_owner_id_created_at", table_name="jobs")
    op.drop_table("jobs")

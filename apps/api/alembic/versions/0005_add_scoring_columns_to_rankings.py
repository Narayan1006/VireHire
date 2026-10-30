"""Add scoring columns to rankings table

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-30 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Add evidence_score float null
    op.add_column("rankings", sa.Column("evidence_score", sa.Float(), nullable=True))

    # 2. Add confidence float not null default 0
    op.add_column(
        "rankings",
        sa.Column("confidence", sa.Float(), server_default=sa.text("0"), nullable=False),
    )

    # 3. Add final_score float null
    op.add_column("rankings", sa.Column("final_score", sa.Float(), nullable=True))

    # 4. Add label varchar(30) null
    op.add_column("rankings", sa.Column("label", sa.String(length=30), nullable=True))

    # 5. Add breakdown jsonb/json not null default '{}'
    if is_postgres:
        breakdown_col = sa.Column(
            "breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        )
    else:
        breakdown_col = sa.Column(
            "breakdown",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        )
    op.add_column("rankings", breakdown_col)

    # 6. Check constraint for valid labels or null
    op.create_check_constraint(
        "ck_rankings_label",
        "rankings",
        "label IS NULL OR label IN ('strong_match', 'needs_review', 'insufficient_evidence')",
    )

    # 7. Composite index for sorting results by job and final_score
    op.create_index("ix_rankings_job_id_final_score", "rankings", ["job_id", "final_score"])


def downgrade() -> None:
    op.drop_index("ix_rankings_job_id_final_score", table_name="rankings")
    op.drop_constraint("ck_rankings_label", "rankings", type_="check")
    op.drop_column("rankings", "breakdown")
    op.drop_column("rankings", "label")
    op.drop_column("rankings", "final_score")
    op.drop_column("rankings", "confidence")
    op.drop_column("rankings", "evidence_score")

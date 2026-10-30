"""Add explanation column to rankings table

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-30 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Add explanation jsonb/json nullable column to rankings table
    if is_postgres:
        explanation_col = sa.Column(
            "explanation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    else:
        explanation_col = sa.Column(
            "explanation",
            sa.JSON(),
            nullable=True,
        )
    op.add_column("rankings", explanation_col)


def downgrade() -> None:
    op.drop_column("rankings", "explanation")

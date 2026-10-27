"""Initial schema with vector extension and users table with RLS

Revision ID: 0001
Revises: 
Create Date: 2026-10-23 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable vector extension in extensions schema
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;")

    # 2. Create users table (id uuid pk, email unique stored lowercase, password_hash, created_at timestamptz)
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        sa.UniqueConstraint('email', name='uq_users_email'),
        sa.CheckConstraint('email = lower(email)', name='ck_users_email_lowercase'),
    )

    # 3. Enable Row Level Security (RLS) on users table with no default policies
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_table('users')
    op.execute("DROP EXTENSION IF EXISTS vector;")

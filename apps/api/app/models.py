"""
SQLAlchemy models for VeriHire v2
"""

import uuid
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = sa.Column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    email = sa.Column(sa.String(320), unique=True, nullable=False)
    password_hash = sa.Column(sa.String(255), nullable=False)
    created_at = sa.Column(
        sa.DateTime(timezone=True),
        default=utc_now,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    )

    jobs = relationship("Job", back_populates="owner", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = sa.Column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id = sa.Column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = sa.Column(sa.String(200), nullable=False)
    description = sa.Column(sa.Text, nullable=False)
    status = sa.Column(
        sa.String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    error = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(
        sa.DateTime(timezone=True),
        default=utc_now,
        server_default=sa.func.now(),
        nullable=False,
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=True),
        default=utc_now,
        server_default=sa.func.now(),
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('draft', 'processing', 'done', 'failed')",
            name="ck_jobs_status",
        ),
        sa.Index("ix_jobs_owner_id_created_at", "owner_id", sa.text("created_at DESC")),
    )

    owner = relationship("User", back_populates="jobs")

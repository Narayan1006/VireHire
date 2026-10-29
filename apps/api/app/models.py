"""
SQLAlchemy models for VeriHire v2
"""

import uuid
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

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
    candidates = relationship("Candidate", back_populates="job", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="job", cascade="all, delete-orphan")


@compiles(sa.schema.Computed, "sqlite")
def compile_computed_sqlite(element, compiler, **kw):
    return ""


@compiles(postgresql.TSVECTOR, "sqlite")
def compile_tsvector_sqlite(element, compiler, **kw):
    return "TEXT"


class PortableVector(TypeDecorator):
    """Maps pgvector Vector(384) on PostgreSQL and JSON on SQLite for tests."""

    impl = sa.types.TypeEngine
    comparator_factory = Vector.comparator_factory
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(384))
        return dialect.type_descriptor(sa.JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            if isinstance(value, (list, tuple)):
                return list(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value


class Candidate(Base):
    __tablename__ = "candidates"

    id = sa.Column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    job_id = sa.Column(
        sa.Uuid,
        sa.ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = sa.Column(sa.String(200), nullable=False)
    email = sa.Column(sa.String(320), nullable=True)
    resume_text = sa.Column(sa.Text, nullable=False)
    links = sa.Column(
        sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'"),
    )
    embedding = sa.Column(PortableVector, nullable=True)
    search_tsv = sa.Column(
        postgresql.TSVECTOR,
        sa.Computed(
            "to_tsvector('english', coalesce(name,'') || ' ' || coalesce(resume_text,''))",
            persisted=True,
        ),
        nullable=True,
    )
    created_at = sa.Column(
        sa.DateTime(timezone=True),
        default=utc_now,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.Index("ix_candidates_job_id", "job_id"),
        sa.Index(
            "ix_candidates_search_tsv",
            "search_tsv",
            postgresql_using="gin",
        ),
        sa.Index(
            "uq_candidates_job_id_email",
            "job_id",
            sa.text("lower(email)"),
            unique=True,
            postgresql_where=sa.text("email IS NOT NULL"),
        ),
    )

    job = relationship("Job", back_populates="candidates")
    rankings = relationship("Ranking", back_populates="candidate", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="candidate", cascade="all, delete-orphan")



class Ranking(Base):
    __tablename__ = "rankings"

    id = sa.Column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    job_id = sa.Column(
        sa.Uuid,
        sa.ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id = sa.Column(
        sa.Uuid,
        sa.ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank = sa.Column(sa.Integer, nullable=False)
    retrieval_score = sa.Column(sa.Float, nullable=False)
    created_at = sa.Column(
        sa.DateTime(timezone=True),
        default=utc_now,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_rankings_job_candidate"),
        sa.Index("ix_rankings_job_id", "job_id"),
    )

    job = relationship("Job", back_populates="rankings")
    candidate = relationship("Candidate", back_populates="rankings")


class Evidence(Base):
    __tablename__ = "evidence"

    id = sa.Column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    candidate_id = sa.Column(
        sa.Uuid,
        sa.ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    source = sa.Column(sa.String(20), nullable=False)
    username = sa.Column(sa.String(100), nullable=True)
    status = sa.Column(sa.String(20), nullable=False)
    reason = sa.Column(sa.String(50), nullable=True)
    payload = sa.Column(
        sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'"),
    )
    fetched_at = sa.Column(
        sa.DateTime(timezone=True),
        default=utc_now,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint("candidate_id", "source", name="uq_evidence_candidate_source"),
        sa.CheckConstraint("source IN ('github', 'leetcode')", name="ck_evidence_source"),
        sa.CheckConstraint("status IN ('verified', 'unverified', 'error')", name="ck_evidence_status"),
        sa.Index("ix_evidence_candidate_id", "candidate_id"),
        sa.Index("ix_evidence_source_username_fetched_at", "source", "username", sa.text("fetched_at DESC")),
    )

    candidate = relationship("Candidate", back_populates="evidence")



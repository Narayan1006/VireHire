"""
VeriHire v2 - Database Connection & Session Management
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_session_factory = None


def configure_engine(engine):
    """
    Attaches a 'connect' event listener to a SQLAlchemy Engine ensuring that every
    new connection sets 'search_path TO public, extensions'.
    This guarantees that pgvector types, operators (e.g. <=>), and extension functions
    located in the 'extensions' schema resolve seamlessly across local containers,
    CI runners, and Supabase's session pooler without requiring ALTER DATABASE or ALTER ROLE.
    """
    @event.listens_for(engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        if getattr(engine.dialect, "name", "") == "postgresql":
            # In psycopg 3, executing in autocommit mode ensures session-level
            # persistence across transactions, pool resets, and rollbacks.
            prev_autocommit = getattr(dbapi_connection, "autocommit", False)
            try:
                dbapi_connection.autocommit = True
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET search_path TO public, extensions")
            except Exception as exc:
                logger.warning("Failed to set search_path on connection: %s", exc)
            finally:
                try:
                    dbapi_connection.autocommit = prev_autocommit
                except Exception:
                    pass

    return engine



def build_engine(database_url: str, **kwargs):
    """
    Builds a SQLAlchemy engine configured for VeriHire:
    - Sets connect_args={'prepare_threshold': None} for pooler safety unless overridden
    - Attaches connect listener to set search_path to 'public, extensions'
    """
    connect_args = kwargs.pop("connect_args", {})
    if "prepare_threshold" not in connect_args:
        connect_args["prepare_threshold"] = None

    engine = create_engine(database_url, connect_args=connect_args, **kwargs)
    configure_engine(engine)
    return engine


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = build_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
            pool_recycle=300,
        )
    return _engine



def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _session_factory


def set_session_factory(factory):
    global _session_factory
    _session_factory = factory



def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a SQLAlchemy database session."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

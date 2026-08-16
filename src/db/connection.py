"""
SurakshaAI — Database Connection
==================================
Manages PostgreSQL connection via SQLAlchemy.

IMPORTANT — Migration strategy:
  - ORM models in src/db/models.py are the source of truth
  - schema.sql is a human-readable reference export only
  - Alembic handles migrations (alembic upgrade head)
  - init_db() uses create_all() for development convenience only
  - Never use init_db() as a production migration mechanism
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from src.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """
    All ORM models inherit from this class.
    """
    pass


def _build_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if settings.is_production():
        return create_engine(
            db_url,
            poolclass=NullPool,
            connect_args={"sslmode": "require"},
            echo=False,
        )
    else:
        return create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,
            echo=settings.DEBUG,
        )


engine = _build_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency: yields a session per request.
    Transaction boundaries are explicit — caller controls commit/rollback.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for use in notebooks and scripts.
    Auto-commits on clean exit, rolls back on exception.

    Usage:
        with db_session() as db:
            db.execute(text("SELECT 1"))
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Create tables using ORM metadata.
    FOR DEVELOPMENT ONLY.
    Use 'alembic upgrade head' in production.
    """
    import src.db.models  # noqa: F401 — registers ORM models with Base
    Base.metadata.create_all(bind=engine)
    logger.info(
        "Database tables created via create_all(). "
        "Use Alembic for production migrations."
    )


def check_db() -> bool:
    """Health check — returns True if database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False
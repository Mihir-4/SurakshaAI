"""
SurakshaAI — Alembic Migration Environment
==========================================
Reads DATABASE_URL from environment / .env file.
Imports all ORM models so Alembic can detect schema changes.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Add project root to path ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Load .env before importing settings ───────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Import Base and all models ────────────────────────────────────────────────
from src.db.connection import Base
import src.db.models  # noqa: F401 — registers all ORM models

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url with DATABASE_URL from environment
db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Check your .env file."
    )
config.set_main_option("sqlalchemy.url", db_url)

# ── Logging ───────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


# ── Migration runners ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL without connecting to the database.
    Useful for reviewing migration SQL before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Connects to the database and applies changes.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
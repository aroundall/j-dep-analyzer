"""Alembic environment configuration.

This module configures Alembic to use the application's database
configuration and SQLModel metadata for migrations.
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlmodel import SQLModel

# Add the src directory to sys.path for imports
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import models to ensure they're registered with SQLModel.metadata
from j_dep_analyzer.db_models import Artifact, DependencyEdge  # noqa: F401, E402
from j_dep_analyzer.config import DatabaseConfig  # noqa: E402
from j_dep_analyzer.db import create_engine_from_config  # noqa: E402

# Alembic Config object
config = context.config

# Configure logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLModel metadata for autogenerate support
target_metadata = SQLModel.metadata


def get_url() -> str:
    """Get database URL from environment configuration.

    For CloudSQL, returns a placeholder URL since we use a custom creator.
    For SQLite, returns the standard SQLite URL.
    """
    db_config = DatabaseConfig.from_env()
    if db_config.db_type == "sqlite":
        return f"sqlite:///{db_config.sqlite_path}"
    # For PostgreSQL with CloudSQL connector, we return a placeholder
    # The actual connection is handled by the connector's creator function
    return "postgresql+pg8000://"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This generates SQL scripts without connecting to the database.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Connects to the database and applies migrations directly.
    """
    db_config = DatabaseConfig.from_env()
    connectable = create_engine_from_config(db_config)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

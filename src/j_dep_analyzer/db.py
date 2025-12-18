"""Database engine creation and initialization.

Supports both SQLite and PostgreSQL via GCP CloudSQL.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

from j_dep_analyzer.config import DatabaseConfig


def create_sqlite_engine(db_path: Path) -> Engine:
    """Create a SQLite engine.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy Engine connected to the SQLite database.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def create_postgresql_engine(config: DatabaseConfig) -> Engine:
    """Create a PostgreSQL engine via GCP CloudSQL connector.

    Uses the Cloud SQL Python Connector for secure connections.
    Supports GCP service account JSON key authentication.

    Args:
        config: Database configuration with CloudSQL connection info.

    Returns:
        SQLAlchemy Engine connected to CloudSQL PostgreSQL.
    """
    from google.cloud.sql.connector import Connector

    # Lazy import to avoid requiring GCP dependencies for SQLite usage
    credentials = None
    if config.gcp_credentials_path and config.gcp_credentials_path.exists():
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            str(config.gcp_credentials_path)
        )

    connector = Connector(credentials=credentials)

    def getconn():
        return connector.connect(
            config.host,  # e.g., "project:region:instance"
            "pg8000",
            user=config.user,
            password=config.password or "",
            db=config.database,
        )

    return create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        echo=False,
    )


def create_engine_from_config(config: DatabaseConfig) -> Engine:
    """Create a database engine based on configuration.

    Args:
        config: Database configuration.

    Returns:
        SQLAlchemy Engine for the configured database.

    Raises:
        ValueError: If the database type is not supported.
    """
    config.validate()

    if config.db_type == "sqlite":
        return create_sqlite_engine(config.sqlite_path)
    elif config.db_type == "postgresql":
        return create_postgresql_engine(config)
    else:
        raise ValueError(f"Unsupported database type: {config.db_type}")


def init_db(engine: Engine) -> None:
    """Initialize database schema using SQLModel metadata.

    Note: This is primarily for development/testing.
    Production should use Alembic migrations.

    Args:
        engine: SQLAlchemy Engine to initialize.
    """
    SQLModel.metadata.create_all(engine)

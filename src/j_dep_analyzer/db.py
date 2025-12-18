"""Database engine creation and initialization.

Supports both SQLite and PostgreSQL via GCP CloudSQL.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlmodel import SQLModel, create_engine

from j_dep_analyzer.config import DatabaseConfig


# Global connector instance to be reused across connections
_connector: Any = None


def _get_connector(credentials: Any = None) -> Any:
    """Get or create a global CloudSQL Connector instance.
    
    Reusing the connector avoids repeated authentication overhead.
    """
    global _connector
    if _connector is None:
        from google.cloud.sql.connector import Connector
        _connector = Connector(credentials=credentials)
    return _connector


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
    Configured with connection pooling for better performance.

    Args:
        config: Database configuration with CloudSQL connection info.

    Returns:
        SQLAlchemy Engine connected to CloudSQL PostgreSQL.
    """
    # Lazy import to avoid requiring GCP dependencies for SQLite usage
    credentials = None
    if config.gcp_credentials_path and config.gcp_credentials_path.exists():
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            str(config.gcp_credentials_path)
        )

    connector = _get_connector(credentials)

    def getconn():
        return connector.connect(
            config.host,  # e.g., "project:region:instance"
            "pg8000",
            user=config.user,
            password=config.password or "",
            db=config.database,
            enable_iam_auth=True,
        )

    # Configure connection pooling for better performance
    # - pool_size: number of connections to keep open
    # - max_overflow: extra connections allowed beyond pool_size
    # - pool_timeout: seconds to wait for a connection from pool
    # - pool_recycle: seconds after which to recycle connections
    # - pool_pre_ping: verify connections are alive before using
    return create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        echo=False,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
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

"""Database configuration module.

Supports both SQLite (for local development) and PostgreSQL via GCP CloudSQL.
Configuration is read from environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration container.

    Attributes:
        db_type: Database type, either "sqlite" or "postgresql"
        sqlite_path: Path to SQLite database file (only for sqlite)
        host: CloudSQL instance connection name (e.g., "project:region:instance")
        database: Database name
        user: Database user
        password: Database password (optional if using IAM auth)
        gcp_credentials_path: Path to GCP service account JSON key file
    """

    db_type: str  # "sqlite" or "postgresql"

    # SQLite config
    sqlite_path: Path | None = None

    # PostgreSQL / CloudSQL config
    host: str | None = None
    database: str | None = None
    user: str | None = None
    password: str | None = None
    gcp_credentials_path: Path | None = None

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables.

        Environment variables:
            JDEP_DB_TYPE: "sqlite" or "postgresql" (default: "sqlite")
            JDEP_DB_PATH: SQLite database path (default: "dependencies.db")
            JDEP_DB_HOST: CloudSQL instance connection name
            JDEP_DB_NAME: Database name (default: "jdep")
            JDEP_DB_USER: Database user
            JDEP_DB_PASSWORD: Database password
            JDEP_GCP_CREDENTIALS: Path to GCP service account JSON key
        """
        db_type = os.getenv("JDEP_DB_TYPE", "sqlite").lower()

        if db_type == "sqlite":
            return cls(
                db_type="sqlite",
                sqlite_path=Path(os.getenv("JDEP_DB_PATH", "dependencies.db")).resolve(),
            )

        # PostgreSQL / CloudSQL configuration
        gcp_creds = os.getenv("JDEP_GCP_CREDENTIALS")

        return cls(
            db_type="postgresql",
            host=os.getenv("JDEP_DB_HOST"),
            database=os.getenv("JDEP_DB_NAME", "jdep"),
            user=os.getenv("JDEP_DB_USER"),
            password=os.getenv("JDEP_DB_PASSWORD"),
            gcp_credentials_path=Path(gcp_creds) if gcp_creds else None,
        )

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If required configuration is missing.
        """
        if self.db_type == "sqlite":
            if not self.sqlite_path:
                raise ValueError("JDEP_DB_PATH is required for SQLite")
        elif self.db_type == "postgresql":
            if not self.host:
                raise ValueError("JDEP_DB_HOST is required for PostgreSQL")
            if not self.user:
                raise ValueError("JDEP_DB_USER is required for PostgreSQL")
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

from __future__ import annotations

from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Artifact(SQLModel, table=True):
    """A Maven artifact stored as a single row.

    We use `gav` (group:artifact:version) as a simple stable primary key.
    DESIGN.md notes that "Unknown" is acceptable when version cannot be resolved.
    """
    gav: str = Field(primary_key=True)
    group_id: str
    artifact_id: str
    version: str


class DependencyEdge(SQLModel, table=True):
    """A dependency edge between two artifacts (A -> B means A depends on B)."""
    __table_args__ = (
        # Prevent duplicate edges when ingesting multiple POMs.
        # We keep scope/optional in the uniqueness key because Maven treats those
        # as meaningful dependency attributes.
        UniqueConstraint("from_gav", "to_gav", "scope", "optional", name="uq_dep_edge"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    from_gav: str = Field(index=True)
    to_gav: str = Field(index=True)
    scope: Optional[str] = Field(default=None)
    optional: Optional[bool] = Field(default=None)

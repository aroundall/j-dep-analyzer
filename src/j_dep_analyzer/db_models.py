from __future__ import annotations

from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Artifact(SQLModel, table=True):
    gav: str = Field(primary_key=True)
    group_id: str
    artifact_id: str
    version: str


class DependencyEdge(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("from_gav", "to_gav", "scope", "optional", name="uq_dep_edge"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    from_gav: str = Field(index=True)
    to_gav: str = Field(index=True)
    scope: Optional[str] = Field(default=None)
    optional: Optional[bool] = Field(default=None)

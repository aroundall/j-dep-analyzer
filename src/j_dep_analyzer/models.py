"""Pydantic models for Maven artifacts and dependencies."""

from __future__ import annotations

from pydantic import BaseModel, Field


UNKNOWN_VERSION = "Unknown"


class GAV(BaseModel):
    """Maven coordinates (GroupId, ArtifactId, Version)."""

    group_id: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    version: str = Field(default=UNKNOWN_VERSION, min_length=1)

    def compact(self) -> str:
        """Return a compact string representation.

        Returns:
            A string like `groupId:artifactId:version`.
        """
        return f"{self.group_id}:{self.artifact_id}:{self.version}"


class Dependency(BaseModel):
    """A Maven dependency entry."""

    gav: GAV
    scope: str | None = None
    optional: bool | None = None

    def label(self) -> str:
        """Return a user-facing label for the dependency.

        Returns:
            A formatted string including GAV and scope when present.
        """
        parts: list[str] = [self.gav.compact()]
        if self.scope:
            parts.append(f"(scope={self.scope})")
        if self.optional is True:
            parts.append("(optional)")
        return " ".join(parts)


class MavenProject(BaseModel):
    """A parsed Maven project model."""

    project: GAV
    dependencies: list[Dependency] = Field(default_factory=list)

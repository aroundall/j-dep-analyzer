"""Initial schema - Create Artifact and DependencyEdge tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-12-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create artifact table
    op.create_table(
        "artifact",
        sa.Column("gav", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("gav"),
    )

    # Create dependencyedge table with indexes and constraints
    op.create_table(
        "dependencyedge",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("from_gav", sa.String(), nullable=False),
        sa.Column("to_gav", sa.String(), nullable=False),
        sa.Column("scope", sa.String(), nullable=True),
        sa.Column("optional", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_gav", "to_gav", "scope", "optional", name="uq_dep_edge"),
    )

    # Create indexes
    op.create_index(
        op.f("ix_dependencyedge_from_gav"),
        "dependencyedge",
        ["from_gav"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dependencyedge_to_gav"),
        "dependencyedge",
        ["to_gav"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_dependencyedge_to_gav"), table_name="dependencyedge")
    op.drop_index(op.f("ix_dependencyedge_from_gav"), table_name="dependencyedge")

    # Drop tables
    op.drop_table("dependencyedge")
    op.drop_table("artifact")

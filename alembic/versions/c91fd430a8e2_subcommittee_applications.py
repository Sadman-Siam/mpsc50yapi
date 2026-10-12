"""add subcommittee applications

Revision ID: c91fd430a8e2
Revises: 8b2a6c4d1f90
Create Date: 2026-10-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "c91fd430a8e2"
down_revision: str | None = "8b2a6c4d1f90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subcommittee_applications",
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("alumna_uuid", sa.Uuid(), nullable=False),
        sa.Column("first_choice", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("second_choice", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("motivation", sa.Text(), nullable=False),
        sa.Column("availability_notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alumna_uuid"], ["alumni.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("alumna_uuid"),
    )


def downgrade() -> None:
    op.drop_table("subcommittee_applications")

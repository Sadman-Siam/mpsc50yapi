"""add open mic entries

Revision ID: a4e0c21f7b63
Revises: df41a2b9c830
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "a4e0c21f7b63"
down_revision: str | None = "df41a2b9c830"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "openmic_entries",
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("alumna_uuid", sa.Uuid(), nullable=False),
        sa.Column("performance_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title_or_description", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("needs_equipment_or_accompaniment", sa.Boolean(), nullable=False),
        sa.Column("equipment_notes", sa.Text(), nullable=True),
        sa.Column("performance_link", sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("scheduled_slot", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alumna_uuid"], ["alumni.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index("ix_openmic_entries_alumna_uuid", "openmic_entries", ["alumna_uuid"])


def downgrade() -> None:
    op.drop_index("ix_openmic_entries_alumna_uuid", table_name="openmic_entries")
    op.drop_table("openmic_entries")

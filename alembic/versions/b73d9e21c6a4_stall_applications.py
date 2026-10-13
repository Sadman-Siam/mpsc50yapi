"""add stall applications

Revision ID: b73d9e21c6a4
Revises: a4e0c21f7b63
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "b73d9e21c6a4"
down_revision: str | None = "a4e0c21f7b63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stall_applications",
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("alumna_uuid", sa.Uuid(), nullable=False),
        sa.Column("stall_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("products", sa.JSON(), nullable=False),
        sa.Column("space_needs", sa.Text(), nullable=False),
        sa.Column("power_needs", sa.Text(), nullable=False),
        sa.Column("number_of_helpers", sa.Integer(), nullable=False),
        sa.Column("contact_phone", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column("website_or_social_link", sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stall_fee_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alumna_uuid"], ["alumni.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("alumna_uuid"),
    )


def downgrade() -> None:
    op.drop_table("stall_applications")

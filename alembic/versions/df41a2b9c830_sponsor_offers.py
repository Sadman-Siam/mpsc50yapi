"""add sponsor offers

Revision ID: df41a2b9c830
Revises: c91fd430a8e2
Create Date: 2026-10-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "df41a2b9c830"
down_revision: str | None = "c91fd430a8e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sponsor_offers",
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("alumna_uuid", sa.Uuid(), nullable=False),
        sa.Column("sponsor_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sponsor_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("contact_person", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("proposed_amount_bdt", sa.Integer(), nullable=True),
        sa.Column("in_kind_description", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alumna_uuid"], ["alumni.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index("ix_sponsor_offers_alumna_uuid", "sponsor_offers", ["alumna_uuid"])


def downgrade() -> None:
    op.drop_index("ix_sponsor_offers_alumna_uuid", table_name="sponsor_offers")
    op.drop_table("sponsor_offers")

"""add alumni referrals

Revision ID: e2c61a4793b0
Revises: b73d9e21c6a4
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e2c61a4793b0"
down_revision: str | None = "b73d9e21c6a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("alumni_profiles") as batch_op:
        batch_op.add_column(sa.Column("referred_by_alumna_uuid", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_alumni_profiles_referred_by_alumna_uuid_alumni",
            "alumni",
            ["referred_by_alumna_uuid"],
            ["uuid"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_alumni_profiles_referred_by_alumna_uuid",
            ["referred_by_alumna_uuid"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("alumni_profiles") as batch_op:
        batch_op.drop_index("ix_alumni_profiles_referred_by_alumna_uuid")
        batch_op.drop_constraint(
            "fk_alumni_profiles_referred_by_alumna_uuid_alumni", type_="foreignkey"
        )
        batch_op.drop_column("referred_by_alumna_uuid")

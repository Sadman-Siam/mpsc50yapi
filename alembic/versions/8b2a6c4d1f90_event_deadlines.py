"""add event submission deadlines

Revision ID: 8b2a6c4d1f90
Revises: 4237ecf23981
Create Date: 2026-10-12
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "8b2a6c4d1f90"
down_revision: str | None = "4237ecf23981"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_deadlines",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_extended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("key"),
    )
    deadlines = sa.table(
        "event_deadlines",
        sa.column("key", sa.String()),
        sa.column("label", sa.String()),
        sa.column("deadline_at", sa.DateTime(timezone=True)),
        sa.column("is_extended", sa.Boolean()),
    )
    op.bulk_insert(
        deadlines,
        [
            {"key": "subcommittee", "label": "Subcommittee submissions", "deadline_at": datetime(2026, 10, 15, 17, 59, 59, tzinfo=UTC), "is_extended": False},
            {"key": "sponsor", "label": "Sponsorship submissions", "deadline_at": datetime(2026, 9, 30, 17, 59, 59, tzinfo=UTC), "is_extended": False},
            {"key": "openmic", "label": "Open mic submissions", "deadline_at": datetime(2026, 11, 15, 17, 59, 59, tzinfo=UTC), "is_extended": False},
            {"key": "stall", "label": "Stall submissions", "deadline_at": datetime(2026, 12, 10, 17, 59, 59, tzinfo=UTC), "is_extended": False},
        ],
    )


def downgrade() -> None:
    op.drop_table("event_deadlines")

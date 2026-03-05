"""Add projected_soc_percent to slot_plans

Revision ID: a0ce8c0ea3b5
Revises: a1b2c3d4e5f6
Create Date: 2026-03-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0ce8c0ea3b5"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add projected_soc_percent column to slot_plans table."""
    op.add_column(
        "slot_plans",
        sa.Column("projected_soc_percent", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Remove projected_soc_percent column from slot_plans table."""
    op.drop_column("slot_plans", "projected_soc_percent")

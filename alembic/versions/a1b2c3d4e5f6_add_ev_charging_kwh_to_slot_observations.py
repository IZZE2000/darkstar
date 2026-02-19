"""Add ev_charging_kwh to slot_observations

Revision ID: a1b2c3d4e5f6
Revises: d8f3a1c9e4b5
Create Date: 2026-02-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "d8f3a1c9e4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ev_charging_kwh column to slot_observations table."""
    op.add_column(
        "slot_observations",
        sa.Column("ev_charging_kwh", sa.Float(), nullable=False, server_default="0.0"),
    )


def downgrade() -> None:
    """Remove ev_charging_kwh column from slot_observations table."""
    op.drop_column("slot_observations", "ev_charging_kwh")

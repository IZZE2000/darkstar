"""Add price_forecasts table for Nordpool spot price forecasting

Revision ID: 5a8b9c2d1e3f
Revises: 1d8d93a90677
Create Date: 2026-03-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision: str = "5a8b9c2d1e3f"
down_revision: str | None = "1d8d93a90677"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create price_forecasts table
    op.create_table(
        "price_forecasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slot_start", sa.String(), nullable=False),
        sa.Column("issue_timestamp", sa.String(), nullable=False),
        sa.Column("days_ahead", sa.Integer(), nullable=False),
        sa.Column("spot_p10", sa.Float(), nullable=True),
        sa.Column("spot_p50", sa.Float(), nullable=True),
        sa.Column("spot_p90", sa.Float(), nullable=True),
        sa.Column("wind_index", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("cloud_cover", sa.Float(), nullable=True),
        sa.Column("radiation_wm2", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_price_forecasts_slot_start", "price_forecasts", ["slot_start"])
    op.create_index(
        "ix_price_forecasts_slot_start_issue_timestamp",
        "price_forecasts",
        ["slot_start", "issue_timestamp"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_price_forecasts_slot_start_issue_timestamp", table_name="price_forecasts")
    op.drop_index("ix_price_forecasts_slot_start", table_name="price_forecasts")

    # Drop table
    op.drop_table("price_forecasts")

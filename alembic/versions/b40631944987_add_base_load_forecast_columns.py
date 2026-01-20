"""add base load forecast columns

Revision ID: b40631944987
Revises: f6c8f45208da
Create Date: 2026-01-19 22:18:25.970805

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b40631944987"
down_revision: str | Sequence[str] | None = "f6c8f45208da"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("slot_forecasts")]

    if "base_load_forecast_kwh" not in columns:
        op.add_column(
            "slot_forecasts",
            sa.Column(
                "base_load_forecast_kwh", sa.Float(), nullable=False, server_default=sa.text("0.0")
            ),
        )
    if "base_load_p10" not in columns:
        op.add_column("slot_forecasts", sa.Column("base_load_p10", sa.Float(), nullable=True))
    if "base_load_p90" not in columns:
        op.add_column("slot_forecasts", sa.Column("base_load_p90", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("slot_forecasts", "base_load_p10")
    op.drop_column("slot_forecasts", "base_load_p90")
    op.drop_column("slot_forecasts", "base_load_forecast_kwh")

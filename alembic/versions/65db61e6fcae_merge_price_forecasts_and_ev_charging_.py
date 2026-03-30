"""Merge price_forecasts and ev_charging branches

Revision ID: 65db61e6fcae
Revises: 5a8b9c2d1e3f, e9f1a2b3c4d5
Create Date: 2026-03-30 09:05:08.594525

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "65db61e6fcae"
down_revision: str | Sequence[str] | None = ("5a8b9c2d1e3f", "e9f1a2b3c4d5")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

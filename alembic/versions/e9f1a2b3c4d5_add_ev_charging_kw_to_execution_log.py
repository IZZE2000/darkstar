"""add ev_charging_kw to execution_log

Revision ID: e9f1a2b3c4d5
Revises: d8f3a1c9e4b5
Create Date: 2026-03-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9f1a2b3c4d5"
down_revision: str | Sequence[str] | None = "a0ce8c0ea3b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "execution_log" in tables:
        columns = [c["name"] for c in inspector.get_columns("execution_log")]
        if "ev_charging_kw" not in columns:
            op.add_column(
                "execution_log",
                sa.Column("ev_charging_kw", sa.Float(), nullable=True),
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "execution_log" in tables:
        columns = [c["name"] for c in inspector.get_columns("execution_log")]
        if "ev_charging_kw" in columns:
            with op.batch_alter_table("execution_log", schema=None) as batch_op:
                batch_op.drop_column("ev_charging_kw")

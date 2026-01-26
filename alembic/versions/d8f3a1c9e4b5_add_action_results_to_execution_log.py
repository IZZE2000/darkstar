"""add action_results to execution_log

Revision ID: d8f3a1c9e4b5
Revises: b4c2b7eb00b2
Create Date: 2026-01-26 21:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8f3a1c9e4b5"
down_revision: str | Sequence[str] | None = "b4c2b7eb00b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "execution_log" in tables:
        columns = [c["name"] for c in inspector.get_columns("execution_log")]
        if "action_results" not in columns:
            with op.batch_alter_table("execution_log", schema=None) as batch_op:
                batch_op.add_column(sa.Column("action_results", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "execution_log" in tables:
        columns = [c["name"] for c in inspector.get_columns("execution_log")]
        if "action_results" in columns:
            with op.batch_alter_table("execution_log", schema=None) as batch_op:
                batch_op.drop_column("action_results")

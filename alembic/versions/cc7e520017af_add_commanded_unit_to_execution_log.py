"""add commanded_unit to execution_log

Revision ID: cc7e520017af
Revises: b40631944987
Create Date: 2026-01-20 08:20:06.060527

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc7e520017af"
down_revision: str | Sequence[str] | None = "b40631944987"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "execution_log" in tables:
        columns = [c["name"] for c in inspector.get_columns("execution_log")]
        if "commanded_unit" not in columns:
            op.add_column(
                "execution_log",
                sa.Column("commanded_unit", sa.String(), nullable=False, server_default="A"),
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "execution_log" in tables:
        columns = [c["name"] for c in inspector.get_columns("execution_log")]
        if "commanded_unit" in columns:
            # SQLite doesn't support DROP COLUMN easily in older versions,
            # but Alembic's batch_alter_table handles it.
            with op.batch_alter_table("execution_log") as batch_op:
                batch_op.drop_column("commanded_unit")

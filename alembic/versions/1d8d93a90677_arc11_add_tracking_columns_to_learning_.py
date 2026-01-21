"""arc11: add tracking columns to learning_runs

Revision ID: 1d8d93a90677
Revises: cc7e520017af
Create Date: 2026-01-21 14:29:36.982210

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1d8d93a90677"
down_revision: str | Sequence[str] | None = "cc7e520017af"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("learning_runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("training_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("models_trained", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("training_duration_seconds", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("partial_failure", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("learning_runs", schema=None) as batch_op:
        batch_op.drop_column("partial_failure")
        batch_op.drop_column("training_duration_seconds")
        batch_op.drop_column("models_trained")
        batch_op.drop_column("training_type")

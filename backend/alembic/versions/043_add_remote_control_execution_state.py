"""add remote control execution state

Revision ID: 043_remote_control_execution_state
Revises: 042_remote_control_queue
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "043_remote_control_execution_state"
down_revision: str | None = "042_remote_control_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("remote_control_commands", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("remote_control_commands", sa.Column("claimed_by_host", sa.String(length=160), nullable=True))
    op.add_column("remote_control_commands", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("remote_control_commands", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("remote_control_commands", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("remote_control_commands", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column("remote_control_commands", sa.Column("result_summary", sa.JSON(), nullable=True))
    op.create_index(
        "ix_remote_control_commands_claimed_by_host",
        "remote_control_commands",
        ["claimed_by_host", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_remote_control_commands_claimed_by_host", table_name="remote_control_commands")
    op.drop_column("remote_control_commands", "result_summary")
    op.drop_column("remote_control_commands", "failure_reason")
    op.drop_column("remote_control_commands", "failed_at")
    op.drop_column("remote_control_commands", "completed_at")
    op.drop_column("remote_control_commands", "started_at")
    op.drop_column("remote_control_commands", "claimed_by_host")
    op.drop_column("remote_control_commands", "claimed_at")

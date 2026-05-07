"""add im message sequence

Revision ID: 035_im_message_sequence
Revises: 034_subscription_events
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "035_im_message_sequence"
down_revision: str | None = "034_subscription_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "im_messages",
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_im_messages_conv_sequence",
        "im_messages",
        ["conversation_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_index("ix_im_messages_conv_sequence", table_name="im_messages")
    op.drop_column("im_messages", "sequence")

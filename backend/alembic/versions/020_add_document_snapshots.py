# -*- coding: utf-8 -*-
"""添加文档版本快照表 document_snapshots

Revision ID: 020_document_snapshots
Revises: 019_ai_assistant
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '020_document_snapshots'
down_revision: Union[str, None] = '019_ai_assistant'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_snapshots',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('session_id', sa.CHAR(36),
                  sa.ForeignKey('document_sessions.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('snapshot_type', sa.String(20), nullable=False, server_default='auto',
                  comment='快照类型: auto | manual | restore'),
        sa.Column('created_by', sa.CHAR(36),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('byte_size', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_document_snapshots_session_id', 'document_snapshots', ['session_id'])
    op.create_index('ix_document_snapshots_version', 'document_snapshots', ['session_id', 'version'])
    op.create_index('ix_document_snapshots_created_by', 'document_snapshots', ['created_by'])


def downgrade() -> None:
    op.drop_table('document_snapshots')

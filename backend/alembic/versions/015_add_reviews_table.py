# -*- coding: utf-8 -*-
"""添加律师评价表

Revision ID: 015_add_reviews
Revises: 014_im_tables
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_utils import safe_create_index, safe_create_table

revision: str = '015_add_reviews'
down_revision: Union[str, None] = '014_im_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    safe_create_table(
        'lawyer_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('lawyer_profile_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('lawyer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('consultation_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('consultations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('delegation_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('delegations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_anonymous', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('reply_content', sa.Text(), nullable=True),
        sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    safe_create_index('ix_lawyer_reviews_profile_created', 'lawyer_reviews', ['lawyer_profile_id', 'created_at'])
    safe_create_index('ix_lawyer_reviews_reviewer', 'lawyer_reviews', ['reviewer_id'])


def downgrade() -> None:
    op.drop_index('ix_lawyer_reviews_reviewer', table_name='lawyer_reviews')
    op.drop_index('ix_lawyer_reviews_profile_created', table_name='lawyer_reviews')
    op.drop_table('lawyer_reviews')

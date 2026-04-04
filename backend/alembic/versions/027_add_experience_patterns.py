# -*- coding: utf-8 -*-
"""add experience_patterns table for Harness learning persistence

Revision ID: 027
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '027_experience_patterns'
down_revision = '026_add_legal_collection_support'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'experience_patterns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=True, index=True),
        sa.Column('pattern', sa.Text(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('solution', sa.Text(), default=''),
        sa.Column('confidence', sa.Float(), default=0.6),
        sa.Column('source', sa.String(20), default='auto'),
        sa.Column('use_count', sa.Integer(), default=0),
        sa.Column('confirmed_count', sa.Integer(), default=0),
        sa.Column('contradicted_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('status', sa.String(20), default='candidate'),  # candidate / validated / deprecated
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('metadata_json', JSONB, default={}),
    )

    op.create_index('idx_exp_user_active', 'experience_patterns', ['user_id', 'is_active'])
    op.create_index('idx_exp_category_confidence', 'experience_patterns', ['category', 'confidence'])
    op.create_index('idx_exp_status', 'experience_patterns', ['status'])


def downgrade():
    op.drop_table('experience_patterns')

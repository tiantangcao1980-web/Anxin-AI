# -*- coding: utf-8 -*-
"""add tasks leads experts courses tables

Revision ID: 1f5e1455247f
Revises: 004_add_sentiment_collaboration
Create Date: 2026-03-17 09:13:31.882460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from migration_utils import safe_create_table

# revision identifiers, used by Alembic.
revision: str = '1f5e1455247f'
down_revision: Union[str, None] = '004_add_sentiment_collaboration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    safe_create_table('courses',
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('instructor', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('duration', sa.String(length=50), nullable=True),
        sa.Column('lessons', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('org_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    safe_create_table('experts',
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('specialty', sa.JSON(), nullable=True),
        sa.Column('years_of_experience', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Float(), nullable=False),
        sa.Column('cases_handled', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('achievements', sa.JSON(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('org_id', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    safe_create_table('leads',
        sa.Column('client_name', sa.String(length=255), nullable=False),
        sa.Column('contact_info', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('case_type', sa.String(length=100), nullable=True),
        sa.Column('estimated_amount', sa.Float(), nullable=False),
        sa.Column('stage', sa.String(length=20), nullable=False),
        sa.Column('follow_ups', sa.JSON(), nullable=True),
        sa.Column('assignee_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('org_id', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    safe_create_table('tasks',
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('assignee_id', sa.UUID(), nullable=True),
        sa.Column('case_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('org_id', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    safe_create_table('course_progress',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('course_id', sa.UUID(), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('completed_lessons', sa.JSON(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('course_progress')
    op.drop_table('tasks')
    op.drop_table('leads')
    op.drop_table('experts')
    op.drop_table('courses')

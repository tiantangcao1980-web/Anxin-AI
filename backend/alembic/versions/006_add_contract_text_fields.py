# -*- coding: utf-8 -*-
"""添加合同文本存储字段

Revision ID: 006_contract_text
Revises: 005_social_login
Create Date: 2026-03-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_contract_text'
down_revision: Union[str, None] = '005_social_login'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加原始合同文本字段
    op.add_column('contracts', sa.Column('original_text', sa.Text(), nullable=True))
    # 添加修改后合同文本字段
    op.add_column('contracts', sa.Column('modified_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('contracts', 'modified_text')
    op.drop_column('contracts', 'original_text')

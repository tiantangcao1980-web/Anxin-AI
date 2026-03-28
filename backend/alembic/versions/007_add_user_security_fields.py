# -*- coding: utf-8 -*-
"""添加用户安全字段

增加 last_login_at、login_attempts、password_changed_at 三个安全相关字段，
用于支持登录锁定、密码策略和审计追踪。

Revision ID: 007_user_security
Revises: 006_contract_text
Create Date: 2026-03-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_user_security'
down_revision: Union[str, None] = '006_contract_text'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 最后登录时间
    op.add_column('users', sa.Column(
        'last_login_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='最后登录时间'
    ))

    # 连续登录失败次数（用于账户锁定）
    op.add_column('users', sa.Column(
        'login_attempts',
        sa.Integer(),
        nullable=False,
        server_default='0',
        comment='连续登录失败次数'
    ))

    # 密码最后修改时间（用于密码过期策略）
    op.add_column('users', sa.Column(
        'password_changed_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='密码最后修改时间'
    ))


def downgrade() -> None:
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'login_attempts')
    op.drop_column('users', 'last_login_at')

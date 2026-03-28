"""添加用户社交登录字段

Revision ID: 005_social_login
Revises: 1f5e1455247f
Create Date: 2026-03-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_social_login'
down_revision: Union[str, None] = '1f5e1455247f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加微信 openid
    op.add_column('users', sa.Column('wechat_openid', sa.String(100), unique=True, nullable=True))
    op.create_index('ix_users_wechat_openid', 'users', ['wechat_openid'])

    # 添加微信 unionid
    op.add_column('users', sa.Column('wechat_unionid', sa.String(100), unique=True, nullable=True))
    op.create_index('ix_users_wechat_unionid', 'users', ['wechat_unionid'])

    # 添加支付宝 user_id
    op.add_column('users', sa.Column('alipay_user_id', sa.String(100), unique=True, nullable=True))
    op.create_index('ix_users_alipay_user_id', 'users', ['alipay_user_id'])

    # 添加登录方式
    op.add_column('users', sa.Column('login_type', sa.String(20), server_default='email', nullable=False))


def downgrade() -> None:
    op.drop_index('ix_users_alipay_user_id', table_name='users')
    op.drop_column('users', 'alipay_user_id')
    op.drop_index('ix_users_wechat_unionid', table_name='users')
    op.drop_column('users', 'wechat_unionid')
    op.drop_index('ix_users_wechat_openid', table_name='users')
    op.drop_column('users', 'wechat_openid')
    op.drop_column('users', 'login_type')

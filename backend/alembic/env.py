"""
Alembic 环境配置
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Windows 事件循环策略修复
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 导入配置和模型
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings
from src.models.base import Base

# 导入所有模型确保它们被注册
from src.models.user import User, Organization
from src.models.case import Case, CaseEvent
from src.models.document import Document, DocumentVersion
from src.models.contract import Contract, ContractClause, ContractRisk
from src.models.conversation import Conversation, Message
from src.models.knowledge import KnowledgeBase, KnowledgeDocument

# Alembic Config 对象
config = context.config

# 设置数据库URL (转换为 asyncpg 格式)
database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
config.set_main_option("sqlalchemy.url", database_url)

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 模型的 MetaData 对象
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式运行迁移
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    异步模式运行迁移
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    在线模式运行迁移
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

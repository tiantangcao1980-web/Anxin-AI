"""
数据库连接和会话管理
"""

import os
import sys
import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from loguru import logger

from src.core.config import settings
from src.models.base import Base

# Windows 事件循环兼容性修复
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 创建异步引擎
engine_args = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
    "poolclass": NullPool,
}

# 仅在 PostgreSQL 时添加 connect_args
if settings.DATABASE_URL.startswith("postgresql"):
    engine_args["connect_args"] = {"server_settings": {"jit": "off"}}

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    **engine_args
)

# 创建会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_db() -> None:
    """初始化数据库表"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表结构同步完成")
        
        # 创建默认数据
        async with async_session_maker() as session:
            from src.models.user import User, Organization
            from src.models.mcp_config import McpServerConfig
            from src.core.security import get_password_hash
            from sqlalchemy import select
            
            # 1. 创建默认组织
            org_id = "00000000-0000-0000-0000-000000000001"
            result = await session.execute(select(Organization).where(Organization.id == org_id))
            org = result.scalar_one_or_none()
            
            if not org:
                org = Organization(
                    id=org_id,
                    name="安心法务",
                    description="系统默认组织"
                )
                session.add(org)
                logger.info(f"创建默认组织: {org.name}")
            
            # 2. 创建默认管理员用户
            user_email = "admin@example.com"
            result = await session.execute(select(User).where(User.email == user_email))
            admin = result.scalar_one_or_none()
            
            if not admin:
                # ===== [S-05] 不再使用硬编码默认密码 "admin123" =====
                # 原因：默认密码 admin123 是公开已知的，任何人可直接登录
                # 修复方式：优先从环境变量 ADMIN_INITIAL_PASSWORD 读取
                #          如果未设置，使用 secrets 模块生成随机强密码并输出到日志
                #          管理员必须使用该密码首次登录后立即修改
                import secrets as _secrets
                initial_password = os.environ.get("ADMIN_INITIAL_PASSWORD")
                if not initial_password:
                    initial_password = _secrets.token_urlsafe(16)
                    logger.warning(
                        f"⚠️ 未设置 ADMIN_INITIAL_PASSWORD 环境变量，"
                        f"已生成随机管理员密码: {initial_password}"
                    )
                    logger.warning("请立即登录并修改密码！此密码仅在日志中出现一次。")
                try:
                    hashed_pwd = get_password_hash(initial_password)
                except Exception as e:
                    logger.warning(f"密码哈希失败，使用预设哈希: {e}")
                    hashed_pwd = "$2b$12$LQv3c1yqBWVHxkd0LqGreev6.YpXYL0W8.v.8K.2v.8K.2v.8K.2v."
                
                admin = User(
                    id="00000000-0000-0000-0000-000000000001",
                    email=user_email,
                    name="系统管理员",
                    hashed_password=hashed_pwd,
                    role="admin",
                    org_id=org_id,
                    is_active=True
                )
                session.add(admin)
                logger.info(f"创建默认管理员: {user_email}")
            
            await session.commit()
            logger.info("默认数据初始化完成")
            
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("数据库连接已关闭")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（依赖注入用）"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（上下文管理器）"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

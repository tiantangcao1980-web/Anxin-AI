"""
数据库连接和会话管理
"""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.models.base import Base

# Windows 事件循环兼容性修复
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 创建异步引擎（启用连接池，替代 NullPool）
# Harness 性能优化: NullPool 每次新建/关闭连接，高并发损失 50-70%
engine_args: dict[str, Any] = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
    "pool_size": settings.DATABASE_POOL_SIZE,       # 默认 10
    "max_overflow": settings.DATABASE_MAX_OVERFLOW,  # 默认 20
    "pool_recycle": 3600,    # 每小时回收（防数据库端超时）
    "pool_timeout": 30,      # 等待可用连接超时
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


async def _ensure_additive_schema_columns() -> None:
    """补齐旧数据库缺失的增量字段。

    本项目当前启动流程依赖 ``create_all``，它能创建缺失的表，但不会为已有表补新列。
    对于已经存在的开发数据库，这会导致代码升级后出现“模型里有字段、库里没字段”的运行时错误。
    这里先对已知高频问题做轻量自修复，避免本地联调被 schema 漂移阻塞。
    """
    if not settings.DATABASE_URL.startswith("postgresql"):
        return

    ddl_statements = [
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS event_type VARCHAR(50)",
        "ALTER TABLE approvals ADD COLUMN IF NOT EXISTS approval_chain JSON",
        "ALTER TABLE approvals ADD COLUMN IF NOT EXISTS current_step INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE approvals ADD COLUMN IF NOT EXISTS template_id UUID",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(30) DEFAULT 'internal' NOT NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS wechat_openid VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS wechat_unionid VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS alipay_user_id VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS login_type VARCHAR(20) DEFAULT 'email' NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_wechat_openid ON users (wechat_openid)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_wechat_unionid ON users (wechat_unionid)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_alipay_user_id ON users (alipay_user_id)",
        "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS original_text TEXT",
        "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS modified_text TEXT",
        "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL",
        "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS esign_flow_id VARCHAR(128)",
        "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS esign_provider VARCHAR(50)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_contracts_esign_flow_id ON contracts (esign_flow_id)",
        "ALTER TABLE webhook_received ADD COLUMN IF NOT EXISTS last_retry_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE webhook_received ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE",
        "CREATE INDEX IF NOT EXISTS ix_webhook_received_next_retry_at ON webhook_received (next_retry_at)",
        "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS external_id VARCHAR(255)",
        "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)",
        "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL",
        "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active' NOT NULL",
        "CREATE INDEX IF NOT EXISTS ix_knowledge_documents_external_id ON knowledge_documents (external_id)",
        # 已有管理员账号自动标记为已验证
        "UPDATE users SET email_verified = true WHERE role IN ('super_admin', 'admin') AND email_verified = false",
        # v2 调查引擎新增字段
        "ALTER TABLE investigations ADD COLUMN IF NOT EXISTS research_data JSON",
        "ALTER TABLE investigations ADD COLUMN IF NOT EXISTS forum_data JSON",
        "ALTER TABLE investigations ADD COLUMN IF NOT EXISTS stages_completed JSON",
        # v3 调查引擎：快照、缓存、偏好表由 create_all 自动创建
        "ALTER TABLE search_cache ADD COLUMN IF NOT EXISTS org_id UUID",
        "CREATE INDEX IF NOT EXISTS ix_search_cache_org_id ON search_cache (org_id)",
        "CREATE INDEX IF NOT EXISTS ix_cache_org_key_source ON search_cache (org_id, cache_key, data_source)",
        "CREATE INDEX IF NOT EXISTS ix_cache_org_company ON search_cache (org_id, company_name)",
        # v4 智能需求发掘引擎：用户 AI 画像
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_profile JSONB DEFAULT '{}'",
        # V2 架构：用户主客户端偏好（needer/provider）
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS primary_client VARCHAR(20) DEFAULT 'needer' NOT NULL",
        "UPDATE users SET user_type = 'internal' WHERE user_type IS NULL",
        # V2 架构：订阅表扩展字段
        "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS client_type VARCHAR(20) DEFAULT 'needer' NOT NULL",
        "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS allowed_modes JSON",
        "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS features_override JSON",
        "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP",
        "ALTER TABLE billing_plans ADD COLUMN IF NOT EXISTS client_type VARCHAR(20) DEFAULT 'needer' NOT NULL",
        # 基于 user_type 推断老用户的 primary_client
        "UPDATE users SET primary_client = 'provider' WHERE user_type IN ('platform_lawyer', 'institution') AND primary_client = 'needer'",
        "UPDATE users SET primary_client = 'needer' WHERE user_type IN ('individual', 'enterprise') AND primary_client != 'needer'",
        # v5 Harness: conversations 表缺失字段修复
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT false",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS starred_at TIMESTAMP",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMP",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT false",
    ]

    async with engine.begin() as conn:
        for ddl in ddl_statements:
            await conn.execute(text(ddl))

    logger.info("数据库增量字段兼容检查完成")


async def _ensure_pre_create_schema_constraints() -> None:
    """补齐 create_all 前必须存在的旧库约束。

    旧开发库可能已存在父表，但缺少新模型声明的复合唯一约束。
    SQLAlchemy 在创建新的子表外键时会先检查父表约束，因此这类修复必须早于
    ``Base.metadata.create_all`` 执行。
    """
    if not settings.DATABASE_URL.startswith("postgresql"):
        return

    ddl_statements = [
        """
        DO $$
        BEGIN
          IF to_regclass('public.capability_routes') IS NOT NULL
             AND NOT EXISTS (
               SELECT 1
               FROM pg_constraint
               WHERE conname = 'uq_capability_routes_org_id'
                 AND conrelid = 'public.capability_routes'::regclass
             )
          THEN
            ALTER TABLE capability_routes
            ADD CONSTRAINT uq_capability_routes_org_id UNIQUE (org_id, id);
          END IF;
        END $$;
        """,
    ]

    async with engine.begin() as conn:
        for ddl in ddl_statements:
            await conn.execute(text(ddl))

    logger.info("数据库建表前兼容约束检查完成")


async def init_db() -> None:
    """初始化数据库表"""
    try:
        await _ensure_pre_create_schema_constraints()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表结构同步完成")
        await _ensure_additive_schema_columns()

        # 创建默认数据
        async with async_session_maker() as session:
            from sqlalchemy import select

            from src.core.security import get_password_hash
            from src.models.user import Organization, User

            # 1. 创建默认组织
            org_id = "00000000-0000-0000-0000-000000000001"
            org_result = await session.execute(select(Organization).where(Organization.id == org_id))
            org = org_result.scalar_one_or_none()

            if not org:
                org = Organization(
                    id=org_id,
                    name="安心智能助手",
                    description="系统默认组织"
                )
                session.add(org)
                logger.info(f"创建默认组织: {org.name}")

            # 2. 创建默认管理员用户
            user_email = "admin@anxinassistant.com"
            admin_result = await session.execute(select(User).where(User.email == user_email))
            admin = admin_result.scalar_one_or_none()

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
                    logger.error(f"密码哈希失败，无法创建管理员账号: {e}")
                    raise RuntimeError("bcrypt 密码哈希失败，请检查依赖安装") from e

                admin = User(
                    id="00000000-0000-0000-0000-000000000001",
                    email=user_email,
                    name="系统管理员",
                    hashed_password=hashed_pwd,
                    role="admin",
                    org_id=org_id,
                    is_active=True,
                    email_verified=True,
                )
                session.add(admin)
                logger.info(f"创建默认管理员: {user_email}")

            await session.commit()
            logger.info("默认数据初始化完成")

        # 初始化预置功能开关（独立事务，不影响主初始化流程）
        try:
            async with async_session_maker() as flag_session:
                from src.services.feature_flag_service import FeatureFlagService
                flag_svc = FeatureFlagService(flag_session)
                await flag_svc.ensure_preset_flags()
                await flag_session.commit()
        except Exception as flag_err:
            logger.warning(f"预置功能开关初始化跳过: {flag_err}")

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

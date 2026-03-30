"""对齐开发数据库的 Alembic 版本状态。

用途：
1. 校验当前数据库是否已具备 head 版本依赖的关键表和增量列
2. 在结构满足要求时，将 alembic_version 安全对齐到最新 revision

说明：
- 仅建议用于本地/开发环境修复 `create_all` 与 Alembic 迁移状态漂移的问题
- 默认 dry-run，只打印检查结果；传入 ``--apply`` 才会实际写入 alembic_version
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import settings
from src.core.database import engine


HEAD_REVISION = "020_document_snapshots"

REQUIRED_TABLES = {
    "approval_templates",
    "notification_preferences",
    "payment_orders",
    "feature_flags",
    "im_conversations",
    "im_participants",
    "im_messages",
    "lawyer_reviews",
    "teams",
    "team_members",
    "case_assignments",
    "time_entries",
    "invoices",
    "lawyer_certifications",
    "lawyer_service_configs",
    "billing_plans",
    "subscriptions",
    "refunds",
    "ai_assistant_configs",
    "conversation_summaries",
    "ai_assistant_feedbacks",
    "document_snapshots",
}

REQUIRED_COLUMNS = {
    "notifications": {"event_type"},
    "approvals": {"approval_chain", "current_step", "template_id"},
}


async def fetch_existing_tables() -> set[str]:
    sql = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )
    async with engine.connect() as conn:
        result = await conn.execute(sql)
        return {row[0] for row in result.fetchall()}


async def fetch_existing_columns(table_name: str) -> set[str]:
    sql = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table_name
        """
    )
    async with engine.connect() as conn:
        result = await conn.execute(sql, {"table_name": table_name})
        return {row[0] for row in result.fetchall()}


async def fetch_current_revision() -> str | None:
    sql = text("SELECT version_num FROM alembic_version LIMIT 1")
    async with engine.connect() as conn:
        result = await conn.execute(sql)
        row = result.first()
        return row[0] if row else None


async def stamp_head() -> None:
    async with engine.begin() as conn:
        current = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        row = current.first()
        if row:
            await conn.execute(
                text("UPDATE alembic_version SET version_num = :revision"),
                {"revision": HEAD_REVISION},
            )
        else:
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": HEAD_REVISION},
            )


async def main(apply: bool) -> int:
    if not settings.DATABASE_URL.startswith("postgresql"):
        print("当前脚本仅支持 PostgreSQL 数据库。")
        return 2

    tables = await fetch_existing_tables()
    missing_tables = sorted(REQUIRED_TABLES - tables)

    missing_columns: dict[str, list[str]] = {}
    for table_name, required in REQUIRED_COLUMNS.items():
        existing = await fetch_existing_columns(table_name)
        diff = sorted(required - existing)
        if diff:
            missing_columns[table_name] = diff

    current_revision = await fetch_current_revision()

    print(f"当前 alembic_version: {current_revision or '<empty>'}")
    print(f"目标 revision: {HEAD_REVISION}")

    if missing_tables:
        print("缺失表：")
        for table_name in missing_tables:
            print(f"  - {table_name}")

    if missing_columns:
        print("缺失列：")
        for table_name, columns in missing_columns.items():
            print(f"  - {table_name}: {', '.join(columns)}")

    if missing_tables or missing_columns:
        print("数据库结构尚未满足对齐条件，未写入 alembic_version。")
        return 1

    print("关键结构检查通过。")

    if not apply:
        print("Dry-run 模式，未写入 alembic_version。使用 --apply 执行对齐。")
        return 0

    await stamp_head()
    print(f"已将 alembic_version 对齐为 {HEAD_REVISION}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="对齐开发数据库的 Alembic 版本状态")
    parser.add_argument("--apply", action="store_true", help="执行写入 alembic_version")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(apply=args.apply)))

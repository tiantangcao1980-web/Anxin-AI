#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回填脚本 —— 把旧 ``users.department`` 字符串字段迁移成 ``DepartmentMembership``

设计见 docs/v3/enterprise-cluster-design.md §8。

行为：
    1. 扫每个 org 的 ``users.department`` 不为空且未在 ``departments`` 表里的部门名
    2. 按 org+部门名 自动建立扁平 ``Department`` 记录（path = /<id>，单层无父）
    3. 为每个 user 建立 ``DepartmentMembership(is_primary=True)``
    4. 幂等：重复跑不会重复建表，不会重复加成员
    5. ``--dry-run`` 模式只打印不写入

用法::

    python3 scripts/migrate-user-department.py            # 真跑
    python3 scripts/migrate-user-department.py --dry-run  # 预览
    python3 scripts/migrate-user-department.py --org-id <id>  # 仅迁移某 org

退出码：
    0 成功
    1 任何运行错误（含 DB 连接失败、参数非法）
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

# 让脚本能 import src.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from src.core.database import async_session_maker  # noqa: E402
from src.models.enterprise_directory import (  # noqa: E402
    Department,
    DepartmentMembership,
)
from src.models.user import User  # noqa: E402


async def migrate(
    session: AsyncSession,
    *,
    dry_run: bool = False,
    only_org: str | None = None,
) -> dict[str, int]:
    """执行回填。返回 ``{"depts_created": N, "memberships_created": M, "users_skipped": K}``。"""
    stats: dict[str, int] = defaultdict(int)

    # 1) 取所有有 department 字符串且关联 org 的用户
    stmt = select(User).where(
        User.department.isnot(None),
        User.org_id.isnot(None),
    )
    if only_org:
        stmt = stmt.where(User.org_id == only_org)
    result = await session.execute(stmt)
    users = list(result.scalars().all())

    if not users:
        print("[migrate] 没有需要迁移的用户")
        return dict(stats)

    # 2) 缓存已有 dept by (org_id, name)
    dept_cache: dict[tuple[str, str], Department] = {}
    dept_stmt = select(Department)
    if only_org:
        dept_stmt = dept_stmt.where(Department.org_id == only_org)
    for d in (await session.execute(dept_stmt)).scalars().all():
        dept_cache[(d.org_id, d.name)] = d

    # 3) 遍历 user → 找 / 建 dept → 建 membership
    for user in users:
        dept_name = (user.department or "").strip()
        if not dept_name or not user.org_id:
            stats["users_skipped"] += 1
            continue

        key = (user.org_id, dept_name)
        dept = dept_cache.get(key)
        if dept is None:
            dept_id = str(uuid4())
            dept = Department(
                id=dept_id,
                org_id=user.org_id,
                name=dept_name,
                parent_id=None,
                path=f"/{dept_id}",
                is_active=True,
                ext_source="migration",
            )
            dept_cache[key] = dept
            if not dry_run:
                session.add(dept)
                await session.flush()
            stats["depts_created"] += 1
            print(f"[migrate] + dept org={user.org_id} name={dept_name!r} id={dept.id}")

        # 检查 membership 是否已存在（幂等）
        existing = await session.execute(
            select(DepartmentMembership).where(
                DepartmentMembership.user_id == user.id,
                DepartmentMembership.department_id == dept.id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            stats["users_skipped"] += 1
            continue

        if not dry_run:
            session.add(
                DepartmentMembership(
                    id=str(uuid4()),
                    user_id=user.id,
                    department_id=dept.id,
                    is_primary=True,
                )
            )
            await session.flush()
        stats["memberships_created"] += 1

    # 注意：``migrate`` 不自己 commit / rollback —— 提交由调用方决定。
    # 这样测试可以用同一 session 跑完后回滚干净，CLI 入口在最外层 commit。
    for key in ("depts_created", "memberships_created", "users_skipped"):
        stats.setdefault(key, 0)
    return dict(stats)


async def _main(args: argparse.Namespace) -> int:
    try:
        async with async_session_maker() as session:
            stats = await migrate(
                session,
                dry_run=args.dry_run,
                only_org=args.org_id,
            )
            if not args.dry_run:
                await session.commit()
        print("[migrate] 完成", stats)
        return 0
    except Exception as exc:
        print(f"[migrate] 失败: {exc}", file=sys.stderr)
        return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="不写库，仅打印")
    p.add_argument("--org-id", type=str, default=None, help="仅迁移指定 org")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(parse_args())))

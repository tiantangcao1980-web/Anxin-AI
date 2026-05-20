# -*- coding: utf-8 -*-
"""
回填脚本 ``scripts/migrate-user-department.py`` 单测

覆盖：
    - 现有 users.department 字符串 → 自动建 Department + Membership
    - 同名部门复用：两个用户共享同一字符串部门 → 只建一条 Department
    - 幂等：再跑一次不产生新记录
    - dry-run 不写库
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Department, DepartmentMembership, Organization, User


def _load_script_module():
    """加载脚本作为模块（脚本带中划线，不能 import）。"""
    path = Path(__file__).resolve().parents[2] / "scripts" / "migrate-user-department.py"
    spec = importlib.util.spec_from_file_location("migrate_user_department", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_user_department"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest_asyncio.fixture
async def script_module():
    return _load_script_module()


@pytest_asyncio.fixture
async def two_orgs_with_users(db_session: AsyncSession):
    """生成 org-A 下三个用户：两人在"技术中心"，一人在"法务中心"。"""
    org_a = Organization(id=str(uuid4()), name="A 公司")
    org_b = Organization(id=str(uuid4()), name="B 公司")
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    users = [
        User(
            id=str(uuid4()),
            email=f"u{i}-{uuid4().hex[:6]}@example.com",
            name=f"User{i}",
            hashed_password="x",
            org_id=org_a.id,
            department=dept,
            is_active=True,
        )
        for i, dept in enumerate(["技术中心", "技术中心", "法务中心"])
    ]
    users.append(
        User(
            id=str(uuid4()),
            email=f"b-{uuid4().hex[:6]}@example.com",
            name="B 用户",
            hashed_password="x",
            org_id=org_b.id,
            department="产品中心",
            is_active=True,
        )
    )
    db_session.add_all(users)
    await db_session.flush()
    return {"org_a": org_a, "org_b": org_b, "users": users}


@pytest.mark.asyncio
async def test_backfill_creates_departments_and_memberships(
    db_session: AsyncSession,
    script_module,
    two_orgs_with_users,
) -> None:
    stats = await script_module.migrate(db_session, dry_run=False)
    assert stats["depts_created"] == 3  # 技术中心 + 法务中心 + 产品中心
    assert stats["memberships_created"] == 4

    # 校验"技术中心"只建了一条
    depts = await db_session.execute(
        select(Department).where(Department.org_id == two_orgs_with_users["org_a"].id)
    )
    dept_names = sorted(d.name for d in depts.scalars().all())
    assert dept_names == ["技术中心", "法务中心"]

    # path 已被设置
    tech = await db_session.execute(
        select(Department).where(
            Department.org_id == two_orgs_with_users["org_a"].id,
            Department.name == "技术中心",
        )
    )
    tech_dept = tech.scalar_one()
    assert tech_dept.path == f"/{tech_dept.id}"
    assert tech_dept.ext_source == "migration"

    # 每个 user 都有一条 membership 且为主部门
    mems = await db_session.execute(select(DepartmentMembership))
    rows = list(mems.scalars().all())
    assert len(rows) == 4
    assert all(m.is_primary for m in rows)


@pytest.mark.asyncio
async def test_backfill_is_idempotent(
    db_session: AsyncSession,
    script_module,
    two_orgs_with_users,
) -> None:
    await script_module.migrate(db_session, dry_run=False)
    second = await script_module.migrate(db_session, dry_run=False)
    assert second["depts_created"] == 0
    assert second["memberships_created"] == 0


@pytest.mark.asyncio
async def test_backfill_dry_run_writes_nothing(
    db_session: AsyncSession,
    script_module,
    two_orgs_with_users,
) -> None:
    stats = await script_module.migrate(db_session, dry_run=True)
    assert stats["depts_created"] == 3
    assert stats["memberships_created"] == 4

    # 但库里没东西
    depts = await db_session.execute(select(Department))
    assert depts.scalars().all() == []
    mems = await db_session.execute(select(DepartmentMembership))
    assert mems.scalars().all() == []


@pytest.mark.asyncio
async def test_backfill_only_org_filter(
    db_session: AsyncSession,
    script_module,
    two_orgs_with_users,
) -> None:
    org_a_id = two_orgs_with_users["org_a"].id
    stats = await script_module.migrate(db_session, dry_run=False, only_org=org_a_id)
    assert stats["depts_created"] == 2
    assert stats["memberships_created"] == 3

    # org_b 不应被触动
    org_b_depts = await db_session.execute(
        select(Department).where(Department.org_id == two_orgs_with_users["org_b"].id)
    )
    assert org_b_depts.scalars().all() == []

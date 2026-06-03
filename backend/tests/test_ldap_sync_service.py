# -*- coding: utf-8 -*-
"""
LdapSyncService 单测

覆盖：
    - 首次同步：从空库 → 创建部门 + 用户 + 主部门 membership
    - 部门 path：父部门优先建，子 path 含父 id
    - 部门改名：第二次同步检测到 name 变更 + 标记 updated
    - 部门消失：deactivate_missing=True 时软删 + 计数
    - 用户消失：login_type=ldap 的不活跃化
    - 邮箱跨租户冲突 → errors 中含说明，不接管
    - dry-run：报告含正确计数但库里没东西
    - InMemoryLdapClient.fetch_users 异常 → 报告含 errors
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Department,
    DepartmentMembership,
    Organization,
    User,
)
from src.services.enterprise_directory import (
    InMemoryLdapClient,
    LdapDeptRecord,
    LdapSyncService,
    LdapUserRecord,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    o = Organization(id=str(uuid4()), name="LDAP 测试集团")
    db_session.add(o)
    await db_session.flush()
    return o


@pytest_asyncio.fixture
async def other_org(db_session: AsyncSession) -> Organization:
    o = Organization(id=str(uuid4()), name="其他租户")
    db_session.add(o)
    await db_session.flush()
    return o


def _dept(dn: str, name: str, parent_dn: str | None = None) -> LdapDeptRecord:
    return LdapDeptRecord(dn=dn, name=name, parent_dn=parent_dn)


def _user(email: str, name: str, dept_dn: str | None) -> LdapUserRecord:
    return LdapUserRecord(
        dn=f"CN={email},{dept_dn or ''}".strip(","),
        email=email,
        name=name,
        external_id=email.split("@")[0],
        department_dn=dept_dn,
    )


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_sync_creates_everything(
    db_session: AsyncSession, org: Organization
) -> None:
    client = InMemoryLdapClient(
        departments=[
            _dept("OU=技术中心,DC=corp", "技术中心"),
            _dept("OU=后端组,OU=技术中心,DC=corp", "后端组", "OU=技术中心,DC=corp"),
        ],
        users=[
            _user("alice@corp.example", "Alice", "OU=后端组,OU=技术中心,DC=corp"),
            _user("bob@corp.example", "Bob", "OU=技术中心,DC=corp"),
        ],
    )
    svc = LdapSyncService(db_session, org_id=org.id, client=client)
    report = await svc.sync_once()

    assert report.departments_created == 2
    assert report.users_created == 2
    assert report.memberships_created == 2
    assert report.errors == []

    # 部门 path 正确
    depts = (await db_session.execute(
        select(Department).where(Department.org_id == org.id)
    )).scalars().all()
    by_name = {d.name: d for d in depts}
    parent = by_name["技术中心"]
    child = by_name["后端组"]
    assert parent.path == f"/{parent.id}"
    assert child.path == f"/{parent.id}/{child.id}"
    assert child.parent_id == parent.id

    # 用户已建
    users = (await db_session.execute(
        select(User).where(User.org_id == org.id)
    )).scalars().all()
    assert {u.email for u in users} == {"alice@corp.example", "bob@corp.example"}
    assert all(u.login_type == "ldap" for u in users)

    # alice 在后端组（主部门）
    mems = (await db_session.execute(
        select(DepartmentMembership)
    )).scalars().all()
    assert len(mems) == 2
    assert all(m.is_primary for m in mems)


@pytest.mark.asyncio
async def test_rename_marks_updated_not_recreated(
    db_session: AsyncSession, org: Organization
) -> None:
    client1 = InMemoryLdapClient(
        departments=[_dept("OU=A,DC=corp", "A")],
        users=[],
    )
    svc = LdapSyncService(db_session, org_id=org.id, client=client1)
    await svc.sync_once()
    dept_id_first = (await db_session.execute(
        select(Department).where(Department.org_id == org.id)
    )).scalar_one().id

    client2 = InMemoryLdapClient(
        departments=[_dept("OU=A,DC=corp", "A 改名了")],
        users=[],
    )
    svc2 = LdapSyncService(db_session, org_id=org.id, client=client2)
    report = await svc2.sync_once()

    assert report.departments_created == 0
    assert report.departments_updated == 1

    dept = (await db_session.execute(
        select(Department).where(Department.org_id == org.id)
    )).scalar_one()
    assert dept.id == dept_id_first  # 没重新建
    assert dept.name == "A 改名了"


@pytest.mark.asyncio
async def test_missing_dept_is_deactivated(
    db_session: AsyncSession, org: Organization
) -> None:
    client1 = InMemoryLdapClient(
        departments=[
            _dept("OU=A,DC=corp", "A"),
            _dept("OU=B,DC=corp", "B"),
        ],
        users=[],
    )
    await LdapSyncService(db_session, org_id=org.id, client=client1).sync_once()

    # 第二次同步：B 消失
    client2 = InMemoryLdapClient(
        departments=[_dept("OU=A,DC=corp", "A")], users=[]
    )
    report = await LdapSyncService(
        db_session, org_id=org.id, client=client2
    ).sync_once()

    assert report.departments_deactivated == 1
    b = (await db_session.execute(
        select(Department).where(
            Department.org_id == org.id,
            Department.external_id == "OU=B,DC=corp",
        )
    )).scalar_one()
    assert b.is_active is False


@pytest.mark.asyncio
async def test_missing_ldap_user_deactivated(
    db_session: AsyncSession, org: Organization
) -> None:
    client1 = InMemoryLdapClient(
        departments=[_dept("OU=A,DC=corp", "A")],
        users=[
            _user("x@corp.example", "X", "OU=A,DC=corp"),
            _user("y@corp.example", "Y", "OU=A,DC=corp"),
        ],
    )
    await LdapSyncService(db_session, org_id=org.id, client=client1).sync_once()

    # y 离职
    client2 = InMemoryLdapClient(
        departments=[_dept("OU=A,DC=corp", "A")],
        users=[_user("x@corp.example", "X", "OU=A,DC=corp")],
    )
    report = await LdapSyncService(
        db_session, org_id=org.id, client=client2
    ).sync_once()

    assert report.users_deactivated == 1
    y = (await db_session.execute(
        select(User).where(User.email == "y@corp.example")
    )).scalar_one()
    assert y.is_active is False


@pytest.mark.asyncio
async def test_cross_tenant_email_collision_reported(
    db_session: AsyncSession,
    org: Organization,
    other_org: Organization,
) -> None:
    # 在 other_org 先建一个 alice
    existing = User(
        id=str(uuid4()),
        email="alice@corp.example",
        name="既有的 Alice",
        hashed_password="x",
        org_id=other_org.id,
        is_active=True,
    )
    db_session.add(existing)
    await db_session.flush()

    client = InMemoryLdapClient(
        departments=[],
        users=[_user("alice@corp.example", "Alice", None)],
    )
    report = await LdapSyncService(
        db_session, org_id=org.id, client=client
    ).sync_once()

    assert report.users_created == 0
    assert any("跨" in e or "其它租户" in e for e in report.errors), report.errors


@pytest.mark.asyncio
async def test_dry_run_writes_nothing(
    db_session: AsyncSession, org: Organization
) -> None:
    client = InMemoryLdapClient(
        departments=[_dept("OU=A,DC=corp", "A")],
        users=[_user("a@corp.example", "A", "OU=A,DC=corp")],
    )
    report = await LdapSyncService(
        db_session, org_id=org.id, client=client
    ).sync_once(dry_run=True)

    assert report.dry_run is True
    assert report.departments_created == 1
    assert report.users_created == 1
    # 库里没东西
    assert (await db_session.execute(select(Department))).scalars().all() == []
    assert (await db_session.execute(select(User).where(User.org_id == org.id))).scalars().all() == []


@pytest.mark.asyncio
async def test_fetch_departments_error_reported(
    db_session: AsyncSession, org: Organization
) -> None:
    class _Broken:
        def fetch_departments(self):
            raise RuntimeError("LDAP down")

        def fetch_users(self):
            return []

    report = await LdapSyncService(
        db_session, org_id=org.id, client=_Broken()
    ).sync_once()
    assert any("fetch_departments" in e for e in report.errors)


@pytest.mark.asyncio
async def test_audit_hook_receives_report(
    db_session: AsyncSession, org: Organization
) -> None:
    captured: list[dict] = []
    client = InMemoryLdapClient(departments=[], users=[])
    await LdapSyncService(
        db_session,
        org_id=org.id,
        client=client,
        audit_hook=captured.append,
    ).sync_once()
    assert len(captured) == 1
    assert captured[0]["org_id"] == org.id
    assert "departments_created" in captured[0]
    assert "users_created" in captured[0]


def test_unknown_conflict_strategy_rejected() -> None:
    with pytest.raises(ValueError):
        LdapSyncService(
            session=None,  # type: ignore[arg-type]
            org_id="x",
            client=InMemoryLdapClient(),
            conflict_strategy="invalid",
        )

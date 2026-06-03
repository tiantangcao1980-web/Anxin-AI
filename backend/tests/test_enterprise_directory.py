# -*- coding: utf-8 -*-
"""
企业内网集群 —— Department / Membership / PermissionResolver 单测

覆盖：
    - 部门创建 + materialized path 维护
    - 部门移动（含成环检测）
    - 用户加入部门 + 主部门切换
    - 角色绑定 grant + 幂等
    - 角色绑定过期判断
    - PermissionResolver：
        * 静态 fallback（旧 user.role）
        * 在 org scope 下命中 org 级 binding
        * 在 dept scope 下命中祖先 dept binding（向下继承）
        * 在父 dept scope 下不命中子 dept binding（反向不继承）
        * 过期 binding 不计入
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import Permission, UserRole
from src.models import Organization, User
from src.services.enterprise_directory import (
    DepartmentService,
    MembershipService,
    PermissionResolver,
    RoleBindingService,
    ScopeLocator,
    ScopeType,
    SubjectType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    o = Organization(id=str(uuid4()), name="测试集团")
    db_session.add(o)
    await db_session.flush()
    return o


@pytest_asyncio.fixture
async def basic_user(db_session: AsyncSession, org: Organization) -> User:
    u = User(
        id=str(uuid4()),
        email=f"u-{uuid4().hex[:8]}@example.com",
        name="员工",
        hashed_password="x",
        org_id=org.id,
        role=UserRole.MEMBER.value,
        is_active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_root_dept_sets_path(db_session: AsyncSession, org: Organization) -> None:
    svc = DepartmentService(db_session)
    d = await svc.create(org_id=org.id, name="技术中心")
    assert d.path == f"/{d.id}"
    assert d.parent_id is None


@pytest.mark.asyncio
async def test_create_child_dept_path_inherits(
    db_session: AsyncSession, org: Organization
) -> None:
    svc = DepartmentService(db_session)
    parent = await svc.create(org_id=org.id, name="技术中心")
    child = await svc.create(org_id=org.id, name="后端组", parent_id=parent.id)
    assert child.path == f"/{parent.id}/{child.id}"


@pytest.mark.asyncio
async def test_move_updates_descendant_paths(
    db_session: AsyncSession, org: Organization
) -> None:
    svc = DepartmentService(db_session)
    root_a = await svc.create(org_id=org.id, name="A")
    root_b = await svc.create(org_id=org.id, name="B")
    child = await svc.create(org_id=org.id, name="子", parent_id=root_a.id)
    grand = await svc.create(org_id=org.id, name="孙", parent_id=child.id)

    # 把 child 移到 B 下，grand 也要跟着搬
    await svc.move(org.id, child.id, root_b.id)
    await db_session.refresh(child)
    await db_session.refresh(grand)

    assert child.parent_id == root_b.id
    assert child.path == f"/{root_b.id}/{child.id}"
    assert grand.path == f"/{root_b.id}/{child.id}/{grand.id}"


@pytest.mark.asyncio
async def test_move_to_own_descendant_rejected(
    db_session: AsyncSession, org: Organization
) -> None:
    svc = DepartmentService(db_session)
    a = await svc.create(org_id=org.id, name="A")
    b = await svc.create(org_id=org.id, name="B", parent_id=a.id)
    with pytest.raises(ValueError):
        await svc.move(org.id, a.id, b.id)


@pytest.mark.asyncio
async def test_build_tree(db_session: AsyncSession, org: Organization) -> None:
    svc = DepartmentService(db_session)
    a = await svc.create(org_id=org.id, name="A")
    await svc.create(org_id=org.id, name="A.1", parent_id=a.id)
    await svc.create(org_id=org.id, name="A.2", parent_id=a.id)
    await svc.create(org_id=org.id, name="B")
    tree = await svc.build_tree(org.id)
    names = sorted(n["name"] for n in tree)
    assert names == ["A", "B"]
    a_node = next(n for n in tree if n["name"] == "A")
    assert sorted(c["name"] for c in a_node["children"]) == ["A.1", "A.2"]


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_membership_add_and_primary(
    db_session: AsyncSession, org: Organization, basic_user: User
) -> None:
    dept_svc = DepartmentService(db_session)
    d1 = await dept_svc.create(org_id=org.id, name="D1")
    d2 = await dept_svc.create(org_id=org.id, name="D2")

    svc = MembershipService(db_session)
    m1 = await svc.add(user_id=basic_user.id, department_id=d1.id, is_primary=True)
    m2 = await svc.add(user_id=basic_user.id, department_id=d2.id, is_primary=False)
    assert m1.is_primary
    assert not m2.is_primary

    # 切换主部门 —— d1 应自动变成非主
    await svc.set_primary(user_id=basic_user.id, department_id=d2.id)
    await db_session.refresh(m1)
    await db_session.refresh(m2)
    assert not m1.is_primary
    assert m2.is_primary

    # 列出
    user_depts = await svc.list_user_departments(basic_user.id)
    assert {d.id for d in user_depts} == {d1.id, d2.id}


# ---------------------------------------------------------------------------
# RoleBinding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_role_binding_grant_idempotent(
    db_session: AsyncSession, org: Organization, basic_user: User
) -> None:
    svc = RoleBindingService(db_session)
    rb1 = await svc.grant(
        org_id=org.id,
        subject_type=SubjectType.USER,
        subject_id=basic_user.id,
        role=UserRole.LAWYER.value,
        scope_type=ScopeType.ORG,
        scope_id=org.id,
    )
    rb2 = await svc.grant(
        org_id=org.id,
        subject_type=SubjectType.USER,
        subject_id=basic_user.id,
        role=UserRole.LAWYER.value,
        scope_type=ScopeType.ORG,
        scope_id=org.id,
        reason="二次授权",
    )
    assert rb1.id == rb2.id
    assert rb2.reason == "二次授权"


@pytest.mark.asyncio
async def test_role_binding_expiration() -> None:
    """is_effective 在过期时返回 False。"""
    from src.models.enterprise_directory import RoleBinding

    past = datetime.now(UTC) - timedelta(seconds=1)
    future = datetime.now(UTC) + timedelta(hours=1)

    rb_expired = RoleBinding(is_active=True, expires_at=past)
    rb_active = RoleBinding(is_active=True, expires_at=future)
    rb_no_expiry = RoleBinding(is_active=True, expires_at=None)
    rb_inactive = RoleBinding(is_active=False, expires_at=future)

    assert not RoleBindingService.is_effective(rb_expired)
    assert RoleBindingService.is_effective(rb_active)
    assert RoleBindingService.is_effective(rb_no_expiry)
    assert not RoleBindingService.is_effective(rb_inactive)


# ---------------------------------------------------------------------------
# PermissionResolver
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolver_fallback_from_user_role(
    db_session: AsyncSession, org: Organization, basic_user: User
) -> None:
    """没有任何绑定时，应回退到 user.role 的静态权限。"""
    basic_user.role = UserRole.LAWYER.value
    await db_session.flush()
    resolver = PermissionResolver(db_session)
    perms = await resolver.resolve(basic_user, ScopeLocator.org(org.id))
    assert Permission.READ_CASES in perms
    assert Permission.WRITE_CASES in perms


@pytest.mark.asyncio
async def test_resolver_org_binding_grants_extra_perms(
    db_session: AsyncSession, org: Organization, basic_user: User
) -> None:
    """org scope 的 partner 角色绑定让 individual_user 多出一堆权限。"""
    basic_user.role = UserRole.INDIVIDUAL_USER.value
    await db_session.flush()

    rb_svc = RoleBindingService(db_session)
    await rb_svc.grant(
        org_id=org.id,
        subject_type=SubjectType.USER,
        subject_id=basic_user.id,
        role=UserRole.PARTNER.value,
        scope_type=ScopeType.ORG,
        scope_id=org.id,
    )

    resolver = PermissionResolver(db_session)
    perms = await resolver.resolve(basic_user, ScopeLocator.org(org.id))
    # partner 拥有 WRITE_CASES，individual_user 没有
    assert Permission.WRITE_CASES in perms
    assert Permission.DELETE_CASES in perms


@pytest.mark.asyncio
async def test_resolver_department_inheritance_downward(
    db_session: AsyncSession, org: Organization, basic_user: User
) -> None:
    """父部门的角色绑定向下继承到子部门 scope。"""
    basic_user.role = UserRole.INDIVIDUAL_USER.value
    await db_session.flush()

    dept_svc = DepartmentService(db_session)
    parent = await dept_svc.create(org_id=org.id, name="法务中心")
    child = await dept_svc.create(org_id=org.id, name="合同组", parent_id=parent.id)

    # 把用户加入子部门
    await MembershipService(db_session).add(
        user_id=basic_user.id, department_id=child.id, is_primary=True
    )

    # 在父部门给 user 绑 lawyer 角色
    await RoleBindingService(db_session).grant(
        org_id=org.id,
        subject_type=SubjectType.USER,
        subject_id=basic_user.id,
        role=UserRole.LAWYER.value,
        scope_type=ScopeType.DEPARTMENT,
        scope_id=parent.id,
    )

    resolver = PermissionResolver(db_session)
    # 查询 child 作用域 → 应继承
    perms_at_child = await resolver.resolve(basic_user, ScopeLocator.department(child.id))
    assert Permission.WRITE_CASES in perms_at_child
    assert Permission.REVIEW_CONTRACTS in perms_at_child


@pytest.mark.asyncio
async def test_resolver_no_upward_inheritance(
    db_session: AsyncSession, org: Organization, basic_user: User
) -> None:
    """子部门的角色绑定不应向上传播到父部门 scope。"""
    basic_user.role = UserRole.INDIVIDUAL_USER.value
    await db_session.flush()

    dept_svc = DepartmentService(db_session)
    parent = await dept_svc.create(org_id=org.id, name="A")
    child = await dept_svc.create(org_id=org.id, name="A.1", parent_id=parent.id)

    await MembershipService(db_session).add(
        user_id=basic_user.id, department_id=child.id, is_primary=True
    )
    await RoleBindingService(db_session).grant(
        org_id=org.id,
        subject_type=SubjectType.USER,
        subject_id=basic_user.id,
        role=UserRole.LAWYER.value,
        scope_type=ScopeType.DEPARTMENT,
        scope_id=child.id,
    )

    resolver = PermissionResolver(db_session)
    # 在父 scope 下，子 scope 的 lawyer 绑定**不应生效**
    perms_at_parent = await resolver.resolve(basic_user, ScopeLocator.department(parent.id))
    assert Permission.WRITE_CASES not in perms_at_parent


@pytest.mark.asyncio
async def test_resolver_expired_binding_ignored(
    db_session: AsyncSession, org: Organization, basic_user: User
) -> None:
    basic_user.role = UserRole.INDIVIDUAL_USER.value
    await db_session.flush()
    await RoleBindingService(db_session).grant(
        org_id=org.id,
        subject_type=SubjectType.USER,
        subject_id=basic_user.id,
        role=UserRole.PARTNER.value,
        scope_type=ScopeType.ORG,
        scope_id=org.id,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    resolver = PermissionResolver(db_session)
    perms = await resolver.resolve(basic_user, ScopeLocator.org(org.id))
    assert Permission.WRITE_CASES not in perms

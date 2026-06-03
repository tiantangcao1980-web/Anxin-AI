# -*- coding: utf-8 -*-
"""
/api/v1/enterprise/* —— 企业内网集群（部门 / 成员 / 群组 / 角色绑定）

设计见 docs/v3/enterprise-cluster-design.md §4。

挂载点（``api/routes/__init__.py``）::

    api_router.include_router(enterprise.router, prefix="/enterprise", tags=["企业内网集群"])

权限：除部分只读 + 自己 effective-permissions 外，全部要求 ``MANAGE_ORGANIZATION``。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import Permission, get_current_user_required, require_permission
from src.models.user import User
from src.services.enterprise_directory import (
    DepartmentNotFoundError,
    DepartmentService,
    MembershipService,
    PermissionResolver,
    RoleBindingService,
    ScopeLocator,
    ScopeType,
    SubjectType,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic DTO
# ---------------------------------------------------------------------------


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: str | None = None
    code: str | None = Field(default=None, max_length=100)
    leader_id: str | None = None
    order_idx: int = 0


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: str | None = None  # 移动


class DepartmentOut(BaseModel):
    id: str
    org_id: str
    parent_id: str | None
    name: str
    code: str | None
    path: str | None
    leader_id: str | None
    order_idx: int
    is_active: bool


class MembershipAdd(BaseModel):
    user_id: str
    is_primary: bool = False
    position_title: str | None = None


class MembershipOut(BaseModel):
    user_id: str
    department_id: str
    is_primary: bool
    position_title: str | None


class RoleBindingCreate(BaseModel):
    subject_type: SubjectType
    subject_id: str
    role: str
    scope_type: ScopeType
    scope_id: str
    expires_at: datetime | None = None
    reason: str | None = None


class RoleBindingOut(BaseModel):
    id: str
    org_id: str
    subject_type: str
    subject_id: str
    role: str
    scope_type: str
    scope_id: str
    is_active: bool
    expires_at: datetime | None
    granted_at: datetime | None
    granted_by: str | None
    reason: str | None


class EffectivePermissionsOut(BaseModel):
    user_id: str
    scope_type: str
    scope_id: str
    permissions: list[str]


# ---------------------------------------------------------------------------
# 部门 API
# ---------------------------------------------------------------------------


@router.get("/organizations/{org_id}/tree", response_model=list[dict])
async def get_department_tree(
    org_id: str = Path(...),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """返回组织的部门树（嵌套结构）。

    只允许查询自己所属租户的树。
    """
    if user.org_id != org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能查询自己组织的部门树")
    svc = DepartmentService(db)
    return await svc.build_tree(org_id)


@router.post(
    "/departments",
    response_model=DepartmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    body: DepartmentCreate,
    user: User = Depends(require_permission(Permission.MANAGE_ORGANIZATION)),
    db: AsyncSession = Depends(get_db),
) -> DepartmentOut:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    svc = DepartmentService(db)
    dept = await svc.create(
        org_id=user.org_id,
        name=body.name,
        parent_id=body.parent_id,
        code=body.code,
        leader_id=body.leader_id,
        order_idx=body.order_idx,
    )
    await db.commit()
    return _dept_to_out(dept)


@router.patch("/departments/{dept_id}", response_model=DepartmentOut)
async def update_department(
    dept_id: str,
    body: DepartmentUpdate,
    user: User = Depends(require_permission(Permission.MANAGE_ORGANIZATION)),
    db: AsyncSession = Depends(get_db),
) -> DepartmentOut:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    svc = DepartmentService(db)
    try:
        if body.name is not None:
            await svc.rename(user.org_id, dept_id, body.name)
        if body.parent_id is not None or "parent_id" in body.model_fields_set:
            await svc.move(user.org_id, dept_id, body.parent_id)
        dept = await svc.get(user.org_id, dept_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    return _dept_to_out(dept)


@router.delete("/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: str,
    user: User = Depends(require_permission(Permission.MANAGE_ORGANIZATION)),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    svc = DepartmentService(db)
    try:
        await svc.soft_delete(user.org_id, dept_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    await db.commit()


# ---------------------------------------------------------------------------
# 成员 API
# ---------------------------------------------------------------------------


@router.get(
    "/departments/{dept_id}/members",
    response_model=list[MembershipOut],
)
async def list_department_members(
    dept_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> list[MembershipOut]:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    # 校验部门属于本租户
    dept_svc = DepartmentService(db)
    try:
        await dept_svc.get(user.org_id, dept_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    svc = MembershipService(db)
    members = await svc.list_department_members(dept_id)
    return [
        MembershipOut(
            user_id=m.user_id,
            department_id=m.department_id,
            is_primary=m.is_primary,
            position_title=m.position_title,
        )
        for m in members
    ]


@router.post(
    "/departments/{dept_id}/members",
    response_model=MembershipOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    dept_id: str,
    body: MembershipAdd,
    user: User = Depends(require_permission(Permission.MANAGE_ORGANIZATION)),
    db: AsyncSession = Depends(get_db),
) -> MembershipOut:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    dept_svc = DepartmentService(db)
    try:
        await dept_svc.get(user.org_id, dept_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    svc = MembershipService(db)
    m = await svc.add(
        user_id=body.user_id,
        department_id=dept_id,
        is_primary=body.is_primary,
        position_title=body.position_title,
    )
    await db.commit()
    return MembershipOut(
        user_id=m.user_id,
        department_id=m.department_id,
        is_primary=m.is_primary,
        position_title=m.position_title,
    )


@router.delete(
    "/departments/{dept_id}/members/{uid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    dept_id: str,
    uid: str,
    user: User = Depends(require_permission(Permission.MANAGE_ORGANIZATION)),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    dept_svc = DepartmentService(db)
    try:
        await dept_svc.get(user.org_id, dept_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    svc = MembershipService(db)
    await svc.remove(user_id=uid, department_id=dept_id)
    await db.commit()


@router.put(
    "/departments/{dept_id}/members/{uid}/primary",
    response_model=MembershipOut,
)
async def set_primary_membership(
    dept_id: str,
    uid: str,
    user: User = Depends(require_permission(Permission.MANAGE_ORGANIZATION)),
    db: AsyncSession = Depends(get_db),
) -> MembershipOut:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    dept_svc = DepartmentService(db)
    try:
        await dept_svc.get(user.org_id, dept_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    svc = MembershipService(db)
    try:
        m = await svc.set_primary(user_id=uid, department_id=dept_id)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    await db.commit()
    return MembershipOut(
        user_id=m.user_id,
        department_id=m.department_id,
        is_primary=m.is_primary,
        position_title=m.position_title,
    )


# ---------------------------------------------------------------------------
# 角色绑定 API
# ---------------------------------------------------------------------------


@router.post(
    "/role-bindings",
    response_model=RoleBindingOut,
    status_code=status.HTTP_201_CREATED,
)
async def grant_role(
    body: RoleBindingCreate,
    user: User = Depends(require_permission(Permission.MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> RoleBindingOut:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    svc = RoleBindingService(db)
    rb = await svc.grant(
        org_id=user.org_id,
        subject_type=body.subject_type,
        subject_id=body.subject_id,
        role=body.role,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        granted_by=user.id,
        expires_at=body.expires_at,
        reason=body.reason,
    )
    await db.commit()
    return _rb_to_out(rb)


@router.delete(
    "/role-bindings/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_role(
    binding_id: str,
    user: User = Depends(require_permission(Permission.MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")
    svc = RoleBindingService(db)
    revoked = await svc.revoke(org_id=user.org_id, binding_id=binding_id)
    if not revoked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "role binding 不存在")
    await db.commit()


# ---------------------------------------------------------------------------
# 有效权限查询（调试 / 审计）
# ---------------------------------------------------------------------------


@router.post(
    "/ldap-sync/trigger",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ldap_sync(
    dry_run: bool = Query(default=False, description="dry-run 模式"),
    user: User = Depends(require_permission(Permission.MANAGE_ORGANIZATION)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """手动触发一次 LDAP / AD 同步（私有化部署 + ad-hoc 兜底）。

    生产环境的 cron 由 ``ldap-sync`` docker service 跑；本接口仅用于：
        - 立即拉取一次（不等下个 interval）
        - dry-run 预览本次同步会改什么
        - 排错用

    需要 ``MANAGE_ORGANIZATION`` 权限 + 环境变量配置 LDAP_* 系列。
    """
    import os as _os

    from src.services.enterprise_directory import (
        Ldap3Client,
        Ldap3Config,
        LdapNotAvailable,
        LdapSyncService,
    )

    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "用户未关联组织")

    # 读 LDAP 环境
    cfg = Ldap3Config(
        url=_os.environ.get("LDAP_URL", ""),
        bind_dn=_os.environ.get("LDAP_BIND_DN", ""),
        bind_password=_os.environ.get("LDAP_BIND_PASSWORD", ""),
        user_base_dn=_os.environ.get("LDAP_USER_BASE_DN", ""),
        dept_base_dn=_os.environ.get("LDAP_DEPT_BASE_DN", ""),
    )
    if not (cfg.url and cfg.user_base_dn and cfg.dept_base_dn):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LDAP 未配置（缺少 LDAP_URL / *_BASE_DN）",
        )

    try:
        client = Ldap3Client(cfg)
        svc = LdapSyncService(db, org_id=user.org_id, client=client)
        report = await svc.sync_once(dry_run=dry_run)
        if not dry_run:
            await db.commit()
    except LdapNotAvailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return report.as_dict()


@router.get(
    "/users/{uid}/effective-permissions",
    response_model=EffectivePermissionsOut,
)
async def get_effective_permissions(
    uid: str,
    scope_type: str = Query(..., pattern="^(org|department)$"),
    scope_id: str = Query(...),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> EffectivePermissionsOut:
    """计算并返回用户在指定作用域下的有效权限。

    权限要求：自己查自己 OR ``MANAGE_ROLES``。
    """
    if uid != user.id:
        from src.core.deps import has_permission
        if not has_permission(user.role, Permission.MANAGE_ROLES):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查询他人的有效权限")

    # 加载 target user
    from sqlalchemy import select as _select
    result = await db.execute(_select(User).where(User.id == uid))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    if target.org_id != user.org_id and user.id != uid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "跨租户访问被禁止")

    scope = (
        ScopeLocator.org(scope_id)
        if scope_type == "org"
        else ScopeLocator.department(scope_id)
    )
    resolver = PermissionResolver(db)
    perms = await resolver.resolve(target, scope)
    return EffectivePermissionsOut(
        user_id=uid,
        scope_type=scope_type,
        scope_id=scope_id,
        permissions=sorted(p.value for p in perms),
    )


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------


def _dept_to_out(d: Any) -> DepartmentOut:
    return DepartmentOut(
        id=d.id,
        org_id=d.org_id,
        parent_id=d.parent_id,
        name=d.name,
        code=d.code,
        path=d.path,
        leader_id=d.leader_id,
        order_idx=d.order_idx,
        is_active=d.is_active,
    )


def _rb_to_out(rb: Any) -> RoleBindingOut:
    return RoleBindingOut(
        id=rb.id,
        org_id=rb.org_id,
        subject_type=rb.subject_type,
        subject_id=rb.subject_id,
        role=rb.role,
        scope_type=rb.scope_type,
        scope_id=rb.scope_id,
        is_active=rb.is_active,
        expires_at=rb.expires_at,
        granted_at=rb.granted_at,
        granted_by=rb.granted_by,
        reason=rb.reason,
    )

# -*- coding: utf-8 -*-
"""
PermissionResolver —— 计算用户在某一作用域下的有效权限

设计见 docs/v3/enterprise-cluster-design.md §3.1-§3.2。

核心算法：

    effective(user, scope=dept_d) =
       ROLE_PERMISSIONS[user.role]                                   # 旧字段 fallback
     ∪ Σ ROLE_PERMISSIONS[r] for r in role_bindings(user, scope=dept_d 及其祖先)
     ∪ Σ ROLE_PERMISSIONS[r] for r in role_bindings(user_groups(user), ...)
     ∪ Σ ROLE_PERMISSIONS[r] for r in role_bindings(user_departments(user), ...)

部门绑定**向下继承**到所有后代部门；反之不成立。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import Permission, get_user_permissions
from src.models.enterprise_directory import (
    Department,
    DepartmentMembership,
    UserGroupMember,
)
from src.models.user import User
from src.services.enterprise_directory.role_binding_service import RoleBindingService


@dataclass(frozen=True, slots=True)
class ScopeLocator:
    """作用域定位 —— 描述"在哪儿"。

    type:
        - ``org``        在整个组织内
        - ``department`` 在某个具体部门（及其后代）
    """

    type: str   # 'org' | 'department'
    id: str     # org_id 或 department_id

    @classmethod
    def org(cls, org_id: str) -> ScopeLocator:
        return cls(type="org", id=org_id)

    @classmethod
    def department(cls, dept_id: str) -> ScopeLocator:
        return cls(type="department", id=dept_id)


class PermissionResolver:
    """有效权限解析器。

    用法::

        resolver = PermissionResolver(session)
        perms = await resolver.resolve(user, ScopeLocator.org(org_id))
        if Permission.WRITE_CASES in perms: ...
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._rb_service = RoleBindingService(session)

    # ------------------------------------------------------------------
    # 公开
    # ------------------------------------------------------------------

    async def resolve(
        self,
        user: User,
        scope: ScopeLocator,
        *,
        now: datetime | None = None,
    ) -> set[Permission]:
        """计算 user 在 scope 下的有效权限集合。

        步骤：
        1. 拉用户静态角色权限（fallback）
        2. 求 scope 在部门树上的"祖先链"（含自己）—— 部门绑定向下继承
        3. 把 user / user 所属部门 / user 所属 group 都当作主体，查全部绑定
        4. 过滤：绑定的 scope 必须**等于或包含** scope（即绑定 scope 是 scope 的祖先或等于）
        5. 过滤：绑定生效（active + 未过期）
        6. 合并所有命中角色对应的 ROLE_PERMISSIONS
        """
        if not user.org_id:
            return set()

        if scope.type not in {"org", "department"}:
            raise ValueError(f"未知 scope.type: {scope.type!r}")

        # 1) 静态 fallback
        permissions: set[Permission] = set(get_user_permissions(user.role))

        # 2) scope 祖先链：部门 → 自己 + 所有祖先 + org；org → 仅 org
        ancestor_scope_ids = await self._collect_scope_ancestors(user.org_id, scope)

        # 3) 主体集合：user 本人 + 所属部门链 + 所属 group
        subjects: list[tuple[str, str]] = [("user", user.id)]

        user_depts = await self._user_department_ids(user.id)
        for dept_id in user_depts:
            subjects.append(("department", dept_id))
            # 部门本身的 binding 视同对该部门的所有成员授权；
            # 部门往上的祖先部门也算（部门 binding 向下继承的对偶）
            dept_chain = await self._department_chain(user.org_id, dept_id)
            for ancestor_id in dept_chain:
                subjects.append(("department", ancestor_id))

        user_groups = await self._user_group_ids(user.id)
        for gid in user_groups:
            subjects.append(("group", gid))

        # 去重（dict.fromkeys 保序）
        subjects = list(dict.fromkeys(subjects))

        # 4) 一次性拉所有相关绑定
        bindings = await self._rb_service.list_for_subjects(
            org_id=user.org_id,
            subjects=subjects,
            active_only=True,
        )

        # 5) 过滤生效 + scope 在祖先链
        for b in bindings:
            if not RoleBindingService.is_effective(b, now=now):
                continue
            if not self._scope_covers(b.scope_type, b.scope_id, ancestor_scope_ids, user.org_id):
                continue
            permissions.update(get_user_permissions(b.role))

        return permissions

    async def has_permission(
        self,
        user: User,
        permission: Permission,
        scope: ScopeLocator,
    ) -> bool:
        """简便函数。"""
        return permission in await self.resolve(user, scope)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    async def _user_department_ids(self, user_id: str) -> list[str]:
        result = await self.session.execute(
            select(DepartmentMembership.department_id).where(
                DepartmentMembership.user_id == user_id
            )
        )
        return [row[0] for row in result.all()]

    async def _user_group_ids(self, user_id: str) -> list[str]:
        result = await self.session.execute(
            select(UserGroupMember.group_id).where(UserGroupMember.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def _department_chain(self, org_id: str, dept_id: str) -> list[str]:
        """返回 dept_id 自己 + 所有祖先 id（基于 materialized path）。"""
        result = await self.session.execute(
            select(Department).where(
                Department.id == dept_id,
                Department.org_id == org_id,
            )
        )
        dept = result.scalar_one_or_none()
        if dept is None or not dept.path:
            return [dept_id] if dept else []
        # path = "/r/a/b" → ["r","a","b"]
        chain = [seg for seg in dept.path.split("/") if seg]
        return chain

    async def _collect_scope_ancestors(self, org_id: str, scope: ScopeLocator) -> set[tuple[str, str]]:
        """生成"覆盖当前 scope 的所有作用域"。

        - 如果 scope=org → {(org, org_id)}
        - 如果 scope=department:d → {(org, org_id)} ∪ {(department, x) for x in d 的祖先链}
        """
        covers: set[tuple[str, str]] = {("org", org_id)}
        if scope.type == "department":
            chain = await self._department_chain(org_id, scope.id)
            for d_id in chain:
                covers.add(("department", d_id))
        return covers

    @staticmethod
    def _scope_covers(
        binding_scope_type: str,
        binding_scope_id: str,
        ancestor_scopes: set[tuple[str, str]],
        org_id: str,
    ) -> bool:
        """绑定的作用域是否覆盖当前查询 scope。

        覆盖 = 绑定 scope ∈ {当前 scope, 当前 scope 的祖先, org}
        """
        return (binding_scope_type, binding_scope_id) in ancestor_scopes

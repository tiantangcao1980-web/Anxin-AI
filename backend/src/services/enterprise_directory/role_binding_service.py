# -*- coding: utf-8 -*-
"""
RoleBindingService —— 角色绑定 CRUD

设计见 docs/v3/enterprise-cluster-design.md §3。
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enterprise_directory import RoleBinding


class SubjectType(str, Enum):
    USER = "user"
    DEPARTMENT = "department"
    GROUP = "group"
    POSITION = "position"


class ScopeType(str, Enum):
    ORG = "org"
    DEPARTMENT = "department"


class RoleBindingService:
    """角色绑定 CRUD。

    使用方式::

        svc = RoleBindingService(session)
        await svc.grant(
            org_id=ctx.org_id,
            subject_type=SubjectType.USER,
            subject_id=user.id,
            role="lawyer",
            scope_type=ScopeType.DEPARTMENT,
            scope_id=dept.id,
            granted_by=admin.id,
        )
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # 写
    # ------------------------------------------------------------------

    async def grant(
        self,
        *,
        org_id: str,
        subject_type: SubjectType | str,
        subject_id: str,
        role: str,
        scope_type: ScopeType | str,
        scope_id: str,
        granted_by: str | None = None,
        expires_at: datetime | None = None,
        reason: str | None = None,
    ) -> RoleBinding:
        """授权（幂等：同样主体/角色/作用域已存在则刷新过期与原因）。"""
        s_type = SubjectType(subject_type).value if not isinstance(subject_type, SubjectType) else subject_type.value
        c_type = ScopeType(scope_type).value if not isinstance(scope_type, ScopeType) else scope_type.value

        existing = await self._find_one(
            org_id=org_id,
            subject_type=s_type,
            subject_id=subject_id,
            role=role,
            scope_type=c_type,
            scope_id=scope_id,
        )
        if existing is not None:
            existing.expires_at = expires_at
            existing.reason = reason
            existing.granted_by = granted_by
            existing.granted_at = datetime.now(UTC)
            existing.is_active = True
            await self.session.flush()
            return existing

        rb = RoleBinding(
            org_id=org_id,
            subject_type=s_type,
            subject_id=subject_id,
            role=role,
            scope_type=c_type,
            scope_id=scope_id,
            granted_by=granted_by,
            granted_at=datetime.now(UTC),
            expires_at=expires_at,
            reason=reason,
            is_active=True,
        )
        self.session.add(rb)
        await self.session.flush()
        return rb

    async def revoke(self, *, org_id: str, binding_id: str) -> bool:
        result = await self.session.execute(
            select(RoleBinding).where(
                RoleBinding.id == binding_id,
                RoleBinding.org_id == org_id,
            )
        )
        rb = result.scalar_one_or_none()
        if rb is None:
            return False
        rb.is_active = False
        await self.session.flush()
        return True

    # ------------------------------------------------------------------
    # 读
    # ------------------------------------------------------------------

    async def list_for_subject(
        self,
        *,
        org_id: str,
        subject_type: SubjectType | str,
        subject_id: str,
        active_only: bool = True,
    ) -> list[RoleBinding]:
        s_type = subject_type.value if isinstance(subject_type, SubjectType) else subject_type
        stmt = select(RoleBinding).where(
            RoleBinding.org_id == org_id,
            RoleBinding.subject_type == s_type,
            RoleBinding.subject_id == subject_id,
        )
        if active_only:
            stmt = stmt.where(RoleBinding.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_subjects(
        self,
        *,
        org_id: str,
        subjects: list[tuple[str, str]],  # (subject_type, subject_id)
        active_only: bool = True,
    ) -> list[RoleBinding]:
        """批量查询多个主体的绑定，一次性返回；解析器用这个减少 SQL 次数。"""
        if not subjects:
            return []
        from sqlalchemy import and_, or_

        clauses = [
            and_(RoleBinding.subject_type == s_type, RoleBinding.subject_id == s_id)
            for s_type, s_id in subjects
        ]
        stmt = select(RoleBinding).where(
            RoleBinding.org_id == org_id,
            or_(*clauses),
        )
        if active_only:
            stmt = stmt.where(RoleBinding.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def is_effective(binding: RoleBinding, *, now: datetime | None = None) -> bool:
        """判断绑定当前是否生效（active + 未过期）。"""
        if not binding.is_active:
            return False
        if binding.expires_at is None:
            return True
        ref = now or datetime.now(UTC)
        # binding.expires_at 可能是 naive，统一处理
        exp = binding.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        return exp > ref

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    async def _find_one(
        self,
        *,
        org_id: str,
        subject_type: str,
        subject_id: str,
        role: str,
        scope_type: str,
        scope_id: str,
    ) -> RoleBinding | None:
        stmt = select(RoleBinding).where(
            RoleBinding.org_id == org_id,
            RoleBinding.subject_type == subject_type,
            RoleBinding.subject_id == subject_id,
            RoleBinding.role == role,
            RoleBinding.scope_type == scope_type,
            RoleBinding.scope_id == scope_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

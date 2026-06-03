# -*- coding: utf-8 -*-
"""
MembershipService —— 用户-部门关系管理

设计见 docs/v3/enterprise-cluster-design.md §3。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enterprise_directory import Department, DepartmentMembership


class MembershipService:
    """成员-部门服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # 写
    # ------------------------------------------------------------------

    async def add(
        self,
        *,
        user_id: str,
        department_id: str,
        is_primary: bool = False,
        position_title: str | None = None,
    ) -> DepartmentMembership:
        """把用户加入部门。

        - 已存在时返回原记录（幂等）
        - is_primary=True 会自动把该用户其它部门的 is_primary 设回 False
        """
        existing = await self._get(user_id, department_id)
        if existing is not None:
            if is_primary and not existing.is_primary:
                await self._unset_primary(user_id, exclude=existing.id)
                existing.is_primary = True
                await self.session.flush()
            return existing

        if is_primary:
            await self._unset_primary(user_id)

        m = DepartmentMembership(
            user_id=user_id,
            department_id=department_id,
            is_primary=is_primary,
            position_title=position_title,
            joined_at=datetime.now(UTC),
        )
        self.session.add(m)
        await self.session.flush()
        return m

    async def remove(self, *, user_id: str, department_id: str) -> bool:
        m = await self._get(user_id, department_id)
        if m is None:
            return False
        m.left_at = datetime.now(UTC)
        await self.session.delete(m)
        await self.session.flush()
        return True

    async def set_primary(self, *, user_id: str, department_id: str) -> DepartmentMembership:
        m = await self._get(user_id, department_id)
        if m is None:
            raise LookupError(f"user={user_id} 不属于 dept={department_id}")
        if not m.is_primary:
            await self._unset_primary(user_id, exclude=m.id)
            m.is_primary = True
            await self.session.flush()
        return m

    # ------------------------------------------------------------------
    # 读
    # ------------------------------------------------------------------

    async def list_user_departments(self, user_id: str) -> list[Department]:
        """返回用户当前所属的所有 *活跃* 部门。"""
        stmt = (
            select(Department)
            .join(DepartmentMembership, DepartmentMembership.department_id == Department.id)
            .where(
                DepartmentMembership.user_id == user_id,
                Department.is_active.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_department_members(self, department_id: str) -> list[DepartmentMembership]:
        stmt = select(DepartmentMembership).where(
            DepartmentMembership.department_id == department_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def primary_department(self, user_id: str) -> Department | None:
        stmt = (
            select(Department)
            .join(DepartmentMembership, DepartmentMembership.department_id == Department.id)
            .where(
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.is_primary.is_(True),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    async def _get(self, user_id: str, department_id: str) -> DepartmentMembership | None:
        result = await self.session.execute(
            select(DepartmentMembership).where(
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.department_id == department_id,
            )
        )
        return result.scalar_one_or_none()

    async def _unset_primary(self, user_id: str, *, exclude: str | None = None) -> None:
        stmt = (
            update(DepartmentMembership)
            .where(
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.is_primary.is_(True),
            )
            .values(is_primary=False)
        )
        if exclude is not None:
            stmt = stmt.where(DepartmentMembership.id != exclude)
        await self.session.execute(stmt)

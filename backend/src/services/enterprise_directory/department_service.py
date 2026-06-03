# -*- coding: utf-8 -*-
"""
DepartmentService —— 部门 CRUD + materialized path 维护

设计见 docs/v3/enterprise-cluster-design.md §2.2 / §2.3。

关键不变量：
    - 每次创建/移动部门都要重算 ``path = parent.path + "/" + dept.id``
    - 移动时**批量更新所有后代**的 path（一次 SQL，按前缀替换）
    - 不允许把节点移动到自己的后代下（成环检测）
"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enterprise_directory import Department


class DepartmentNotFoundError(LookupError):
    """部门不存在或不属于当前租户。"""


class DepartmentService:
    """部门服务。

    所有方法都强制 ``org_id`` 隔离 —— 跨租户访问直接 ``DepartmentNotFoundError``。
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get(self, org_id: str, dept_id: str) -> Department:
        result = await self.session.execute(
            select(Department).where(
                Department.id == dept_id,
                Department.org_id == org_id,
            )
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise DepartmentNotFoundError(f"department={dept_id} 不存在或不属于 org={org_id}")
        return dept

    async def list_by_org(self, org_id: str, *, include_inactive: bool = False) -> list[Department]:
        stmt = select(Department).where(Department.org_id == org_id)
        if not include_inactive:
            stmt = stmt.where(Department.is_active.is_(True))
        result = await self.session.execute(stmt.order_by(Department.order_idx, Department.name))
        return list(result.scalars().all())

    async def descendants(self, org_id: str, dept_id: str) -> list[Department]:
        """返回 dept_id 自己 + 所有后代（含自己）。

        基于 materialized path 的 LIKE 前缀查询。
        """
        dept = await self.get(org_id, dept_id)
        path_prefix = (dept.path or "") + "/"
        stmt = select(Department).where(
            Department.org_id == org_id,
            (Department.path == dept.path) | (Department.path.like(f"{path_prefix}%")),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 创建 / 修改 / 删除
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        org_id: str,
        name: str,
        parent_id: str | None = None,
        code: str | None = None,
        leader_id: str | None = None,
        external_id: str | None = None,
        ext_source: str | None = None,
        order_idx: int = 0,
    ) -> Department:
        parent_path = ""
        if parent_id:
            parent = await self.get(org_id, parent_id)
            parent_path = parent.path or f"/{parent.id}"

        dept = Department(
            org_id=org_id,
            parent_id=parent_id,
            name=name,
            code=code,
            leader_id=leader_id,
            external_id=external_id,
            ext_source=ext_source,
            order_idx=order_idx,
        )
        self.session.add(dept)
        await self.session.flush()  # 拿到 id

        dept.path = f"{parent_path}/{dept.id}" if parent_path else f"/{dept.id}"
        await self.session.flush()
        return dept

    async def rename(self, org_id: str, dept_id: str, name: str) -> Department:
        dept = await self.get(org_id, dept_id)
        dept.name = name
        await self.session.flush()
        return dept

    async def move(self, org_id: str, dept_id: str, new_parent_id: str | None) -> Department:
        """把 dept 挂到新父节点下，批量更新所有后代 path。

        - new_parent_id=None → 设为根
        - 禁止把节点移到自己的后代下（会成环）
        """
        dept = await self.get(org_id, dept_id)
        old_path = dept.path or f"/{dept.id}"

        if new_parent_id:
            new_parent = await self.get(org_id, new_parent_id)
            if (new_parent.path or "").startswith(old_path + "/") or new_parent.id == dept.id:
                raise ValueError("不能把部门移动到自己的后代下")
            new_path_root = new_parent.path or f"/{new_parent.id}"
            new_path = f"{new_path_root}/{dept.id}"
        else:
            new_path = f"/{dept.id}"

        # 批量替换前缀：自身 + 所有后代
        # SQL: UPDATE departments SET path = REPLACE(path, :old, :new)
        #      WHERE org_id = :org AND (path = :old OR path LIKE :old || '/%')
        from sqlalchemy import func

        await self.session.execute(
            update(Department)
            .where(
                Department.org_id == org_id,
                (Department.path == old_path) | (Department.path.like(f"{old_path}/%")),
            )
            .values(path=func.replace(Department.path, old_path, new_path))
        )
        dept.parent_id = new_parent_id
        await self.session.flush()
        # 重新加载以拿到更新后的 path
        await self.session.refresh(dept)
        return dept

    async def soft_delete(self, org_id: str, dept_id: str) -> None:
        """软删除：仅置 is_active=False。后代不级联（由调用方决定）。"""
        dept = await self.get(org_id, dept_id)
        dept.is_active = False
        await self.session.flush()

    # ------------------------------------------------------------------
    # 树视图
    # ------------------------------------------------------------------

    async def build_tree(self, org_id: str) -> list[dict]:
        """返回部门树（list of nested dict）。

        简单实现：一次性拉所有，O(N) 拼树。规模 ≤ 数千节点都够。
        """
        depts = await self.list_by_org(org_id, include_inactive=True)
        by_id: dict[str, dict] = {
            d.id: {
                "id": d.id,
                "name": d.name,
                "code": d.code,
                "parent_id": d.parent_id,
                "path": d.path,
                "leader_id": d.leader_id,
                "is_active": d.is_active,
                "order_idx": d.order_idx,
                "children": [],
            }
            for d in depts
        }
        roots: list[dict] = []
        for d in depts:
            node = by_id[d.id]
            if d.parent_id and d.parent_id in by_id:
                by_id[d.parent_id]["children"].append(node)
            else:
                roots.append(node)
        # 子节点稳定排序
        for node in by_id.values():
            node["children"].sort(key=lambda x: (x["order_idx"], x["name"]))
        roots.sort(key=lambda x: (x["order_idx"], x["name"]))
        return roots

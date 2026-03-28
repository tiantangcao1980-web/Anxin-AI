# -*- coding: utf-8 -*-
"""
律师精英服务
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.expert import Expert


class ExpertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_experts(
        self,
        org_id: Optional[str] = None,
        specialty: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[Expert], int]:
        query = select(Expert)
        if org_id:
            query = query.where(Expert.org_id == org_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(Expert.rating.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        experts = list(result.scalars().all())

        # 后过滤 specialty（JSON 字段）
        if specialty:
            experts = [e for e in experts if specialty in (e.specialty or [])]

        return experts, total

    async def get_expert(self, expert_id: str) -> Optional[Expert]:
        result = await self.db.execute(select(Expert).where(Expert.id == expert_id))
        return result.scalar_one_or_none()

    async def create_expert(self, **kwargs) -> Expert:
        expert = Expert(**kwargs)
        self.db.add(expert)
        await self.db.flush()
        return expert

    async def update_expert(self, expert_id: str, org_id: Optional[str] = None, **kwargs) -> Optional[Expert]:
        query = select(Expert).where(Expert.id == expert_id)
        if org_id:
            query = query.where(Expert.org_id == org_id)
        result = await self.db.execute(query)
        expert = result.scalar_one_or_none()
        if not expert:
            return None
        for k, v in kwargs.items():
            if hasattr(expert, k) and v is not None:
                setattr(expert, k, v)
        await self.db.flush()
        return expert

    async def delete_expert(self, expert_id: str, org_id: Optional[str] = None) -> bool:
        query = select(Expert).where(Expert.id == expert_id)
        if org_id:
            query = query.where(Expert.org_id == org_id)
        result = await self.db.execute(query)
        expert = result.scalar_one_or_none()
        if not expert:
            return False
        await self.db.delete(expert)
        await self.db.flush()
        return True

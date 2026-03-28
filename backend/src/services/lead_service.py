# -*- coding: utf-8 -*-
"""
案源管理服务
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.lead import Lead


class LeadService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_leads(
        self,
        org_id: Optional[str] = None,
        stage: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[Lead], int]:
        query = select(Lead)
        if org_id:
            query = query.where(Lead.org_id == org_id)
        if stage:
            query = query.where(Lead.stage == stage)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_lead(self, lead_id: str) -> Optional[Lead]:
        result = await self.db.execute(select(Lead).where(Lead.id == lead_id))
        return result.scalar_one_or_none()

    async def create_lead(self, **kwargs) -> Lead:
        lead = Lead(**kwargs)
        self.db.add(lead)
        await self.db.flush()
        return lead

    async def update_lead(self, lead_id: str, org_id: Optional[str] = None, **kwargs) -> Optional[Lead]:
        query = select(Lead).where(Lead.id == lead_id)
        if org_id:
            query = query.where(Lead.org_id == org_id)
        result = await self.db.execute(query)
        lead = result.scalar_one_or_none()
        if not lead:
            return None
        for k, v in kwargs.items():
            if hasattr(lead, k) and v is not None:
                setattr(lead, k, v)
        await self.db.flush()
        return lead

    async def update_stage(self, lead_id: str, stage: str, org_id: Optional[str] = None) -> Optional[Lead]:
        return await self.update_lead(lead_id, org_id=org_id, stage=stage)

    async def add_follow_up(self, lead_id: str, follow_up: dict, org_id: Optional[str] = None) -> Optional[Lead]:
        query = select(Lead).where(Lead.id == lead_id)
        if org_id:
            query = query.where(Lead.org_id == org_id)
        result = await self.db.execute(query)
        lead = result.scalar_one_or_none()
        if not lead:
            return None
        current = lead.follow_ups or []
        import uuid
        follow_up["id"] = str(uuid.uuid4())[:8]
        lead.follow_ups = current + [follow_up]
        await self.db.flush()
        return lead

    async def delete_lead(self, lead_id: str, org_id: Optional[str] = None) -> bool:
        query = select(Lead).where(Lead.id == lead_id)
        if org_id:
            query = query.where(Lead.org_id == org_id)
        result = await self.db.execute(query)
        lead = result.scalar_one_or_none()
        if not lead:
            return False
        await self.db.delete(lead)
        await self.db.flush()
        return True

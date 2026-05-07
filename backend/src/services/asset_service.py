"""
资产管理服务
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.asset import Asset


class AssetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_assets(self, org_id: str) -> list[Asset]:
        result = await self.db.execute(
            select(Asset).where(Asset.org_id == org_id).order_by(Asset.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_asset(
        self,
        name: str,
        asset_type: str,
        original_value: float,
        current_value: float,
        acquisition_date: date | None,
        org_id: str,
        created_by: str,
    ) -> Asset:
        asset = Asset(
            name=name,
            asset_type=asset_type,
            original_value=original_value,
            current_value=current_value,
            acquisition_date=acquisition_date,
            org_id=org_id,
            created_by=created_by,
        )
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def update_asset(
        self,
        asset_id: str,
        org_id: str | None = None,
        **kwargs: Any,
    ) -> Asset | None:
        query = select(Asset).where(Asset.id == asset_id)
        if org_id:
            query = query.where(Asset.org_id == org_id)
        result = await self.db.execute(query)
        asset = result.scalar_one_or_none()
        if not asset:
            return None

        for k, v in kwargs.items():
            if hasattr(asset, k) and v is not None:
                setattr(asset, k, v)

        await self.db.flush()
        return asset

    async def delete_asset(self, asset_id: str, org_id: str | None = None) -> bool:
        query = select(Asset).where(Asset.id == asset_id)
        if org_id:
            query = query.where(Asset.org_id == org_id)
        result = await self.db.execute(query)
        asset = result.scalar_one_or_none()
        if not asset:
            return False

        await self.db.delete(asset)
        await self.db.flush()
        return True

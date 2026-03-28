# -*- coding: utf-8 -*-

import hashlib
import time
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.models.feature_flag import FeatureFlag


class FeatureFlagService:
    # 进程内缓存（类级别共享）
    _cache: Optional[list] = None
    _cache_ts: float = 0.0
    _CACHE_TTL: float = 30.0  # 缓存有效期 30 秒

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def _invalidate_cache(cls) -> None:
        """清除进程内缓存"""
        cls._cache = None
        cls._cache_ts = 0.0

    async def list_all(self) -> list[FeatureFlag]:
        # 优先读取进程内缓存（TTL 30s）
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_ts) < self._CACHE_TTL:
            return self._cache
        result = await self.db.execute(
            select(FeatureFlag).order_by(FeatureFlag.created_at.desc())
        )
        flags = list(result.scalars().all())
        # 写入缓存
        FeatureFlagService._cache = flags
        FeatureFlagService._cache_ts = time.monotonic()
        return flags

    async def get_by_key(self, key: str) -> Optional[FeatureFlag]:
        result = await self.db.execute(
            select(FeatureFlag).where(FeatureFlag.key == key)
        )
        return result.scalar_one_or_none()

    async def get_flags_for_user(
        self,
        user_id: str,
        role: str,
        org_id: Optional[str] = None,
    ) -> dict[str, bool]:
        flags = await self.list_all()
        result: dict[str, bool] = {}
        for flag in flags:
            result[flag.key] = self._evaluate(flag, user_id, role, org_id)
        return result

    async def evaluate_flag(
        self,
        key: str,
        user_id: str,
        role: str,
        org_id: Optional[str] = None,
    ) -> bool:
        flag = await self.get_by_key(key)
        if not flag:
            return False
        return self._evaluate(flag, user_id, role, org_id)

    def _evaluate(
        self,
        flag: FeatureFlag,
        user_id: str,
        role: str,
        org_id: Optional[str],
    ) -> bool:
        if not flag.enabled:
            return False

        if flag.expires_at and flag.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return False

        if flag.target_roles and role not in flag.target_roles:
            return False

        if flag.target_org_ids and (not org_id or org_id not in flag.target_org_ids):
            return False

        if flag.rollout_percentage < 10000:
            hash_val = int(hashlib.md5(f"{user_id}:{flag.key}".encode()).hexdigest(), 16)
            if hash_val % 10000 >= flag.rollout_percentage:
                return False

        return True

    async def create(self, data: dict) -> FeatureFlag:
        flag = FeatureFlag(**data)
        self.db.add(flag)
        await self.db.flush()
        self._invalidate_cache()
        return flag

    async def update(self, key: str, data: dict) -> Optional[FeatureFlag]:
        flag = await self.get_by_key(key)
        if not flag:
            return None
        for k, v in data.items():
            if hasattr(flag, k) and v is not None:
                setattr(flag, k, v)
        await self.db.flush()
        self._invalidate_cache()
        return flag

    async def delete(self, key: str) -> bool:
        flag = await self.get_by_key(key)
        if not flag:
            return False
        await self.db.delete(flag)
        await self.db.flush()
        self._invalidate_cache()
        return True

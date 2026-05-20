import hashlib
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.feature_flag import FeatureFlag


class FeatureFlagService:
    # 进程内缓存（类级别共享）
    _cache: list[FeatureFlag] | None = None
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
        result = await self.db.execute(select(FeatureFlag).order_by(FeatureFlag.created_at.desc()))
        flags = list(result.scalars().all())
        # 写入缓存
        FeatureFlagService._cache = flags
        FeatureFlagService._cache_ts = time.monotonic()
        return flags

    async def get_by_key(self, key: str) -> FeatureFlag | None:
        result = await self.db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
        return result.scalar_one_or_none()

    async def get_flags_for_user(
        self,
        user_id: str,
        role: str,
        org_id: str | None = None,
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
        org_id: str | None = None,
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
        org_id: str | None,
    ) -> bool:
        if not flag.enabled:
            return False

        if flag.expires_at and flag.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            return False

        if flag.target_roles and role not in flag.target_roles:
            return False

        if flag.target_org_ids and (not org_id or org_id not in flag.target_org_ids):
            return False

        rollout_percentage = (
            flag.rollout_percentage if flag.rollout_percentage is not None else 10000
        )
        if rollout_percentage < 10000:
            hash_val = int(hashlib.md5(f"{user_id}:{flag.key}".encode()).hexdigest(), 16)
            if hash_val % 10000 >= rollout_percentage:
                return False

        return True

    async def create(self, data: dict[str, Any]) -> FeatureFlag:
        flag = FeatureFlag(**data)
        self.db.add(flag)
        await self.db.flush()
        self._invalidate_cache()
        return flag

    async def update(self, key: str, data: dict[str, Any]) -> FeatureFlag | None:
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

    async def ensure_preset_flags(self) -> int:
        """
        确保所有前端功能模块的预置 flags 存在于数据库中。
        不覆盖已有配置，仅创建缺失的记录。默认全部启用。

        Returns:
            新创建的 flag 数量
        """
        from loguru import logger

        preset_flags = [
            # AI 智能助手
            ("ai_chat", "智能对话", "AI 法律助手对话系统"),
            ("ai_assistant", "AI 助手增强", "智能推荐、自动摘要等增强功能"),
            # 智能协作
            ("case_management", "案件管理", "案件全生命周期管理"),
            ("contract_management", "合同管理", "合同审查、模板管理、签约流程"),
            ("document_management", "智能文档", "文档协作工作台"),
            ("lawyer_matching", "找律师", "律师智能匹配与推荐"),
            ("approval_workflow", "审批流程", "多级审批与模板配置"),
            # 智能调查
            ("due_diligence", "尽职调查", "企业背景调查"),
            # 法律智库
            ("knowledge_graph", "知识图谱", "法律知识图谱可视化"),
            ("knowledge_base", "法律智库", "法律法规数据库"),
            # 通讯
            ("im_messaging", "即时通讯", "团队内部即时消息"),
            ("collaboration", "在线协作", "多人实时文档协作"),
            # 律师生态
            ("lawyer_onboarding", "律师入驻", "律师认证入驻"),
            ("lawyer_dashboard", "律师工作台", "律师专属工作台"),
            ("customer_acquisition", "获客管理", "客户获取渠道分析"),
            # 商业化
            ("pricing", "定价页", "产品定价与套餐选择"),
            ("my_subscription", "我的订阅", "用户订阅管理"),
            ("billing", "计费管理", "计费规则与订单管理"),
            # 系统
            ("private_llm", "私有大模型", "私有化大模型部署"),
            ("settings", "系统设置", "个人偏好与通知设置"),
            ("private_deployment", "私有化部署", "企业私有化部署支持"),
            ("firm_management", "律所管理", "律所信息与成员管理"),
            ("enterprise_management", "企业管理", "企业信息与合规配置"),
        ]

        # 一次查出所有已有 keys
        existing = await self.list_all()
        existing_keys = {f.key for f in existing}

        created = 0
        for key, name, desc in preset_flags:
            if key not in existing_keys:
                flag = FeatureFlag(
                    key=key,
                    name=name,
                    description=desc,
                    enabled=True,
                    rollout_percentage=10000,
                )
                self.db.add(flag)
                created += 1

        if created > 0:
            await self.db.flush()
            self._invalidate_cache()
            logger.info(
                f"预置功能开关: 新建 {created} 个，跳过 {len(preset_flags) - created} 个已有记录"
            )
        else:
            logger.debug("预置功能开关: 全部已存在，无需创建")

        return created

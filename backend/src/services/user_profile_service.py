"""
用户画像服务 (User Profile Service)

为每个用户建立持久化 AI 画像，实现：
1. 法律专业度自动推断（基于用词复杂度）
2. 常用场景统计（自动更新场景权重）
3. 追问耐心度追踪（基于历史行为自适应）
4. 默认上下文积累（减少重复追问）
5. 交互统计（总会话数、平均反馈评分等）
"""

from datetime import datetime
from typing import Any, cast

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User

# 默认画像结构
DEFAULT_AI_PROFILE: dict[str, Any] = {
    "legal_sophistication": "intermediate",  # novice / intermediate / expert
    "industry": "",
    "common_scenarios": {},  # {"CONTRACT_REVIEW": 12, "LABOR_HR": 5}
    "clarification_patience": 0.8,  # 0-1，值越高越有耐心
    "preferred_detail_level": "balanced",  # concise / balanced / detailed
    "default_context": {},  # {"company_type": "科技公司", "jurisdiction": "北京"}
    "interaction_stats": {
        "total_sessions": 0,
        "clarification_rounds_total": 0,
        "clarification_abandon_count": 0,
        "feedback_ratings_sum": 0,
        "feedback_ratings_count": 0,
    },
    "updated_at": None,
}

# 法律专业术语集（用于推断用户专业度）
_EXPERT_TERMS = {
    "不可抗力", "违约金", "约定管辖", "仲裁条款", "竞业限制",
    "善意取得", "表见代理", "缔约过失", "情势变更", "代位权",
    "撤销权", "格式条款", "诉讼时效", "连带责任", "担保物权",
    "股东代表诉讼", "对赌协议", "优先清算权", "反稀释",
    "个人信息保护法", "GDPR", "合规体检", "尽调",
}

_NOVICE_INDICATORS = {
    "请问", "不太懂", "什么意思", "怎么办", "能不能",
    "帮我看看", "我不知道", "我想了解", "帮帮忙",
}


class UserProfileService:
    """用户画像管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user_id: str) -> dict[str, Any]:
        """
        加载用户 AI 画像，不存在则返回默认值。
        """
        result = await self.db.execute(
            select(User.ai_profile).where(User.id == user_id)
        )
        raw_profile = result.scalar_one_or_none()
        if raw_profile and isinstance(raw_profile, dict):
            row = cast(dict[str, Any], raw_profile)
            # 合并默认值确保字段完整
            profile = {**DEFAULT_AI_PROFILE, **row}
            profile["interaction_stats"] = {
                **DEFAULT_AI_PROFILE["interaction_stats"],
                **row.get("interaction_stats", {}),
            }
            return profile
        return dict(DEFAULT_AI_PROFILE)

    async def save_profile(self, user_id: str, profile: dict[str, Any]) -> None:
        """持久化用户画像到数据库"""
        profile["updated_at"] = datetime.now().isoformat()
        await self.db.execute(
            update(User).where(User.id == user_id).values(ai_profile=profile)
        )
        await self.db.flush()

    async def update_after_session(
        self,
        user_id: str,
        intent: str,
        clarification_rounds: int = 0,
        clarification_abandoned: bool = False,
        user_input_sample: str = "",
        feedback_rating: int | None = None,
    ) -> None:
        """
        会话结束后更新用户画像。

        Args:
            user_id: 用户ID
            intent: 本次会话识别的意图
            clarification_rounds: 本次追问轮数
            clarification_abandoned: 用户是否中途放弃追问
            user_input_sample: 用户输入样本（用于推断专业度）
            feedback_rating: 用户反馈评分 (1-5)
        """
        profile = await self.get_profile(user_id)
        stats = profile.get("interaction_stats", {})

        # 1. 更新场景使用频率
        scenarios = profile.get("common_scenarios", {})
        scenarios[intent] = scenarios.get(intent, 0) + 1
        profile["common_scenarios"] = scenarios

        # 2. 更新交互统计
        stats["total_sessions"] = stats.get("total_sessions", 0) + 1
        stats["clarification_rounds_total"] = (
            stats.get("clarification_rounds_total", 0) + clarification_rounds
        )
        if clarification_abandoned:
            stats["clarification_abandon_count"] = (
                stats.get("clarification_abandon_count", 0) + 1
            )

        if feedback_rating is not None:
            stats["feedback_ratings_sum"] = (
                stats.get("feedback_ratings_sum", 0) + feedback_rating
            )
            stats["feedback_ratings_count"] = (
                stats.get("feedback_ratings_count", 0) + 1
            )

        # 3. 更新追问耐心度（滑动加权平均）
        total_sessions = stats["total_sessions"]
        abandon_count = stats.get("clarification_abandon_count", 0)
        if total_sessions > 3:
            # 放弃率越高 → 耐心度越低
            abandon_rate = abandon_count / total_sessions
            profile["clarification_patience"] = round(
                max(0.3, min(1.0, 1.0 - abandon_rate * 1.5)), 2
            )

        # 4. 推断法律专业度（基于用词）
        if user_input_sample:
            profile["legal_sophistication"] = self._infer_sophistication(
                user_input_sample, profile.get("legal_sophistication", "intermediate")
            )

        profile["interaction_stats"] = stats
        await self.save_profile(user_id, profile)
        logger.debug(
            f"用户画像已更新: user={user_id}, intent={intent}, "
            f"patience={profile['clarification_patience']}, "
            f"sophistication={profile['legal_sophistication']}"
        )

    async def get_clarification_config(
        self, user_id: str, intent: str
    ) -> dict[str, Any]:
        """
        根据用户画像返回追问配置（置信度门控 + 耐心度自适应）。

        Returns:
            {
                "max_rounds": int,        # 最大追问轮数
                "max_questions": int,      # 每轮最多问题数
                "use_structured_ui": bool, # 是否使用结构化 UI
                "pre_filled_context": dict,# 预填上下文
                "patience_level": str,     # high / medium / low
            }
        """
        profile = await self.get_profile(user_id)
        patience = profile.get("clarification_patience", 0.8)

        # 追问耐心度分级
        if patience >= 0.7:
            patience_level = "high"
            max_rounds = 2
            max_questions = 3
            use_structured = True
        elif patience >= 0.4:
            patience_level = "medium"
            max_rounds = 1
            max_questions = 2
            use_structured = True
        else:
            patience_level = "low"
            max_rounds = 1
            max_questions = 1
            use_structured = False  # 低耐心用户用自然追问

        # 如果该场景用户用了很多次，减少追问
        scenario_count = profile.get("common_scenarios", {}).get(intent, 0)
        if scenario_count > 10:
            max_questions = max(1, max_questions - 1)

        return {
            "max_rounds": max_rounds,
            "max_questions": max_questions,
            "use_structured_ui": use_structured,
            "pre_filled_context": profile.get("default_context", {}),
            "patience_level": patience_level,
            "legal_sophistication": profile.get("legal_sophistication", "intermediate"),
        }

    async def update_default_context(
        self, user_id: str, key: str, value: str
    ) -> None:
        """将用户经常提供的信息自动存入默认上下文"""
        profile = await self.get_profile(user_id)
        ctx = profile.get("default_context", {})
        ctx[key] = value
        profile["default_context"] = ctx
        await self.save_profile(user_id, profile)

    @staticmethod
    def _infer_sophistication(text: str, current: str) -> str:
        """基于用词推断法律专业度"""
        expert_hits = sum(1 for term in _EXPERT_TERMS if term in text)
        novice_hits = sum(1 for term in _NOVICE_INDICATORS if term in text)

        if expert_hits >= 2:
            return "expert"
        if expert_hits >= 1 and novice_hits == 0:
            # 有专业术语但不确定是否 expert，保持或提升
            return "expert" if current == "expert" else "intermediate"
        if novice_hits >= 2 and expert_hits == 0:
            return "novice"

        return current  # 无明确信号，保持不变

# -*- coding: utf-8 -*-
"""
用户偏好与长期记忆服务 (Preference Service v2)

升级为 DB 持久化模式，基于 User.ai_profile JSON 字段。
兼容原有接口，同时新增与 UserProfileService 的集成。
"""

from typing import Dict, Any, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user_profile_service import UserProfileService


class PreferenceService:
    """用户偏好服务（v2 — DB 持久化版）"""

    def __init__(self, db: Optional[AsyncSession] = None):
        self._db = db
        self._profile_svc: Optional[UserProfileService] = None
        # 内存缓存兜底（无 DB session 时使用）
        self._memory_fallback: Dict[str, Dict[str, Any]] = {}

    def _ensure_profile_svc(self) -> Optional[UserProfileService]:
        if self._profile_svc is None and self._db is not None:
            self._profile_svc = UserProfileService(self._db)
        return self._profile_svc

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有偏好"""
        default_prefs = {
            "professional_level": "intermediate",
            "communication_style": "formal",
            "legal_domain_focus": ["corporate", "contract"],
            "risk_tolerance": "conservative",
            "output_format": "markdown",
            "language": "zh_CN",
        }

        svc = self._ensure_profile_svc()
        if svc:
            profile = await svc.get_profile(user_id)
            # 从 AI 画像中提取偏好
            sophistication = profile.get("legal_sophistication", "intermediate")
            detail_level = profile.get("preferred_detail_level", "balanced")

            level_map = {"novice": "junior", "intermediate": "mid", "expert": "senior"}
            style_map = {"concise": "concise", "balanced": "formal", "detailed": "detailed"}

            default_prefs["professional_level"] = level_map.get(sophistication, "mid")
            default_prefs["communication_style"] = style_map.get(detail_level, "formal")

            # 从场景统计推断关注领域
            scenarios = profile.get("common_scenarios", {})
            if scenarios:
                domain_map = {
                    "CONTRACT_REVIEW": "contract", "LABOR_HR": "labor",
                    "IP_PROTECTION": "ip", "LITIGATION_STRATEGY": "litigation",
                    "TAX_FINANCE": "tax", "REGULATORY_MONITORING": "compliance",
                }
                top_scenarios = sorted(scenarios.items(), key=lambda x: x[1], reverse=True)[:3]
                default_prefs["legal_domain_focus"] = [
                    domain_map.get(s, "general") for s, _ in top_scenarios
                ]

            risk = profile.get("default_context", {}).get("risk_tolerance", "conservative")
            default_prefs["risk_tolerance"] = risk
        else:
            # 内存兜底
            user_prefs = self._memory_fallback.get(user_id, {})
            default_prefs.update(user_prefs)

        return default_prefs

    async def update_preference(self, user_id: str, key: str, value: Any) -> bool:
        """更新单个偏好设置"""
        svc = self._ensure_profile_svc()
        if svc:
            profile = await svc.get_profile(user_id)
            ctx = profile.get("default_context", {})
            ctx[key] = value
            profile["default_context"] = ctx
            await svc.save_profile(user_id, profile)
        else:
            if user_id not in self._memory_fallback:
                self._memory_fallback[user_id] = {}
            self._memory_fallback[user_id][key] = value
        logger.info(f"用户 {user_id} 更新偏好: {key} = {value}")
        return True

    async def batch_update_preferences(self, user_id: str, prefs: Dict[str, Any]) -> bool:
        """批量更新偏好"""
        for key, value in prefs.items():
            await self.update_preference(user_id, key, value)
        return True

    async def get_agent_system_prompt_suffix(self, user_id: str) -> str:
        """根据用户偏好生成 System Prompt 后缀"""
        prefs = await self.get_user_preferences(user_id)

        style_map = {
            "formal": "请使用非常正式、严谨的法律专业术语进行回答。",
            "casual": "请使用通俗易懂、口语化的语言进行解释。",
            "detailed": "请提供尽可能详尽的分析和背景信息。",
            "concise": "请直接给出结论，简明扼要，通过要点形式列出。",
        }

        risk_map = {
            "conservative": "在风险评估时，请采取保守策略，充分提示所有潜在风险。",
            "aggressive": "在风险评估时，请采取积极策略，重点关注解决方案的可行性。",
        }

        level_map = {
            "junior": "用户可能对法律不太熟悉，请避免过多专业术语，多用类比解释。",
            "mid": "用户有一定法律知识，可以使用专业术语但需要适当解释。",
            "senior": "用户是法律专业人士，可以直接使用专业术语和法条引用。",
        }

        suffix = f"""
\n\n【用户个性化偏好】
1. 语言风格：{style_map.get(prefs['communication_style'], '')}
2. 风险偏好：{risk_map.get(prefs['risk_tolerance'], '')}
3. 专业适配：{level_map.get(prefs['professional_level'], '')}
4. 你的回答必须符合上述偏好设定。
"""
        return suffix


# 全局实例（兼容旧代码，无 DB 时内存兜底）
preference_service = PreferenceService()

"""
用户偏好与长期记忆服务 (Preference Service)
负责管理用户的个性化设置、职业背景、习惯偏好等长期记忆。
"""

from typing import Dict, Any, Optional
from loguru import logger
import json

class PreferenceService:
    
    def __init__(self):
        # 模拟数据库存储
        # user_id -> preferences
        self._storage: Dict[str, Dict[str, Any]] = {}
        logger.info("用户偏好服务初始化完成")

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有偏好"""
        # 默认偏好
        default_prefs = {
            "professional_level": "senior", # junior, mid, senior
            "communication_style": "formal", # formal, casual, detailed, concise
            "legal_domain_focus": ["corporate", "contract"], # 关注领域
            "risk_tolerance": "conservative", # conservative, aggressive
            "output_format": "markdown",
            "language": "zh_CN"
        }
        
        user_prefs = self._storage.get(user_id, {})
        # 合并默认值
        return {**default_prefs, **user_prefs}

    async def update_preference(self, user_id: str, key: str, value: Any) -> bool:
        """更新单个偏好设置"""
        if user_id not in self._storage:
            self._storage[user_id] = {}
        
        self._storage[user_id][key] = value
        logger.info(f"用户 {user_id} 更新偏好: {key} = {value}")
        return True

    async def batch_update_preferences(self, user_id: str, prefs: Dict[str, Any]) -> bool:
        """批量更新偏好"""
        if user_id not in self._storage:
            self._storage[user_id] = {}
            
        self._storage[user_id].update(prefs)
        return True

    async def get_agent_system_prompt_suffix(self, user_id: str) -> str:
        """根据用户偏好生成 System Prompt 的后缀，用于个性化 Agent 行为"""
        prefs = await self.get_user_preferences(user_id)
        
        style_map = {
            "formal": "请使用非常正式、严谨的法律专业术语进行回答。",
            "casual": "请使用通俗易懂、口语化的语言进行解释。",
            "detailed": "请提供尽可能详尽的分析和背景信息。",
            "concise": "请直接给出结论，简明扼要，通过要点形式列出。"
        }
        
        risk_map = {
            "conservative": "在风险评估时，请采取保守策略，充分提示所有潜在风险。",
            "aggressive": "在风险评估时，请采取积极策略，重点关注解决方案的可行性。"
        }
        
        suffix = f"""
\n\n【用户个性化偏好】
1. 语言风格：{style_map.get(prefs['communication_style'], "")}
2. 风险偏好：{risk_map.get(prefs['risk_tolerance'], "")}
3. 你的回答必须符合上述偏好设定。
"""
        return suffix

# 全局实例
preference_service = PreferenceService()

# -*- coding: utf-8 -*-
"""
V3 user-facing personas（流程管家、市场研究员、出海贸易官 等）

与 ``backend/src/agents/`` 下 21 个 specialized agent 并存：
    - specialized agent  → 单一原子能力（合同审查 / 法律计算 / 风险评估…），
                           被 coordinator 编排，不直接面向最终用户
    - persona agent      → C 端面向用户的「角色化」入口，背后调用多个
                           specialized agent + skills + 第三方应用，
                           对应 docs/v3/AGENT_PERSONAS.md 定义的 10 个 persona

P7 实施分阶段：
    P7-A → 流程管家（operations_manager）  ✅ 本阶段
    P7-B → 市场研究员（market_researcher）
    P7-C → 出海贸易官（trade_officer）
    P7-D → 内容总监（content_director）
    P7-E → 文档秘书（doc_secretary）
"""

from src.agents.personas.base_persona import BasePersonaAgent, PersonaInfo
from src.agents.personas.registry import PersonaRegistry, get_persona_registry
from src.agents.personas.operations_manager import OperationsManagerAgent

__all__ = [
    "BasePersonaAgent",
    "PersonaInfo",
    "PersonaRegistry",
    "get_persona_registry",
    "OperationsManagerAgent",
]

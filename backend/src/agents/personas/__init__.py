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

# P8-A: 顶层 import 全部 5 个 persona class，确保 ``__init_subclass__``
# 在包加载阶段就触发自动注册，调用方无需依赖 ``autoload()`` 才能拿全。
from src.agents.personas.operations_manager import OperationsManagerAgent
from src.agents.personas.market_researcher import MarketResearcherAgent
from src.agents.personas.lead_hunter import LeadHunterAgent
from src.agents.personas.content_director import ContentDirectorAgent
from src.agents.personas.ecommerce_assistant import EcommerceAssistantAgent
# P9-A: 安心助理（通用入口 + 任务编排）
from src.agents.personas.anxin_assistant import AnxinAssistantAgent

__all__ = [
    "BasePersonaAgent",
    "PersonaInfo",
    "PersonaRegistry",
    "get_persona_registry",
    "OperationsManagerAgent",
    "MarketResearcherAgent",
    "LeadHunterAgent",
    "ContentDirectorAgent",
    "EcommerceAssistantAgent",
    "AnxinAssistantAgent",
]

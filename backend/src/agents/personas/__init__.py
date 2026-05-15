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

# P9-A: 安心助理（通用入口 + 任务编排）
from src.agents.personas.anxin_assistant import AnxinAssistantAgent
from src.agents.personas.base_persona import BasePersonaAgent, PersonaInfo
from src.agents.personas.content_director import ContentDirectorAgent

# P9-C: 合同管家（包装 6 contract agent）
from src.agents.personas.contract_steward import ContractStewardPersona

# P9-D: 尽调专家（包装 3 specialized agent + 关系图谱）
from src.agents.personas.due_diligence_expert import DueDiligenceExpertPersona
from src.agents.personas.ecommerce_assistant import EcommerceAssistantAgent
from src.agents.personas.lead_hunter import LeadHunterAgent

# P9-B: 法律顾问（包装 5 specialized agent）
from src.agents.personas.legal_advisor import LegalAdvisorPersona
from src.agents.personas.market_researcher import MarketResearcherAgent

# P8-A: 顶层 import 全部 5 个 persona class，确保 ``__init_subclass__``
# 在包加载阶段就触发自动注册，调用方无需依赖 ``autoload()`` 才能拿全。
from src.agents.personas.operations_manager import OperationsManagerAgent
from src.agents.personas.registry import PersonaRegistry, get_persona_registry

# P9-E: 财税顾问（包装 2 specialized agent + 跨境 VAT）
from src.agents.personas.tax_finance_advisor import TaxFinanceAdvisorPersona

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
    "LegalAdvisorPersona",
    "ContractStewardPersona",
    "DueDiligenceExpertPersona",
    "TaxFinanceAdvisorPersona",
]

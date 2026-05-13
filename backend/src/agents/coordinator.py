"""
协调调度智能体 (v2 - 性能优化版)

优化点：
1. 消除 _init_agent() 重复调用 — 使用 system_prompt_override 参数
2. 意图识别增加缓存（相同输入短时间内复用结果）
3. 增加更多意图的模板化快速路径，减少不必要的 LLM DAG 规划调用
"""

import hashlib
import json
import re
import time
from typing import Any, cast

from loguru import logger

from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt
from src.services.scenario_templates import (
    assess_completeness,
    build_context_summary,
    get_template_context_for_llm,
)

# 意图代码 → 中文标签映射
INTENT_LABELS: dict[str, str] = {
    "QA_CONSULTATION": "法律咨询",
    "CONTRACT_REVIEW": "合同审查",
    "DUE_DILIGENCE": "尽职调查",
    "DOCUMENT_DRAFTING": "文书起草",
    "LITIGATION_STRATEGY": "诉讼策略",
    "IP_PROTECTION": "知识产权保护",
    "REGULATORY_MONITORING": "合规监管",
    "TAX_FINANCE": "财税合规",
    "LABOR_HR": "劳动人事",
    "EVIDENCE_PROCESSING": "证据处理",
    "E_SIGNATURE": "电子签约",
    "CONTRACT_MANAGEMENT": "合同管理",
    "POLICY_DISTRIBUTION": "制度分发",
    "FIND_LAWYER": "找律师",
    "DEBT_COLLECTION": "债务催收",
    "CORPORATE_GOVERNANCE": "公司治理",
    "FAMILY_LAW": "婚姻家庭",
    "REAL_ESTATE": "房产纠纷",
    "CRIMINAL": "刑事相关",
    "INVESTMENT_FINANCING": "融资投资",
    "MA_RESTRUCTURING": "并购重组",
    "CROSS_BORDER": "跨境涉外",
    "DATA_COMPLIANCE": "数据合规",
    "ANTI_UNFAIR_COMPETITION": "反不正当竞争",
    "FRANCHISE_DISTRIBUTION": "特许经营与经销",
    "CONSTRUCTION_ENGINEERING": "建设工程",
    "GOVERNMENT_CONTRACTS": "政府采购与PPP",
    "BANKRUPTCY_INSOLVENCY": "破产与清算",
    "ENVIRONMENTAL_COMPLIANCE": "环保合规",
    "ANTI_CORRUPTION": "反商业贿赂",
    "PRODUCT_LIABILITY": "产品责任",
    "LEGAL_CALCULATION": "法务分析",
    "CONSUMER_PROTECTION": "消费者维权",
    "TRAFFIC_ACCIDENT": "交通事故",
    "INSURANCE_CLAIM": "保险理赔",
    "SOCIAL_INSURANCE": "社保公积金",
    "PROPERTY_MANAGEMENT": "物业管理",
    "COMPLEX_TASK": "复合任务",
}

_FALLBACK_INTENT_PROMPT = "你是一个专业的法务意图识别专家。"

_FALLBACK_COORDINATOR_PROMPT = "你是AI 智能助手系统的核心协调调度专家。"

# ========== 意图到 Agent 的模板化快速路径映射 ==========
# 这些意图可以不经过 LLM DAG 规划，直接生成固定计划
FAST_PATH_ROUTES: dict[str, list[dict[str, Any]]] = {
    "QA_CONSULTATION": [{"id": "task_1", "agent": "legal_advisor", "depends_on": []}],
    "CONTRACT_REVIEW": [
        {"id": "task_1", "agent": "contract_reviewer", "depends_on": []},
        {
            "id": "task_2",
            "agent": "risk_assessor",
            "instruction_suffix": "基于合同审查结果，评估综合风险。",
            "depends_on": ["task_1"],
        },
    ],
    "DUE_DILIGENCE": [
        {"id": "task_1", "agent": "due_diligence", "depends_on": []},
    ],
    "DOCUMENT_DRAFTING": [
        {"id": "task_1", "agent": "document_drafter", "depends_on": []},
    ],
    "LITIGATION_STRATEGY": [
        {
            "id": "task_1",
            "agent": "legal_researcher",
            "instruction_suffix": "查找相关法条和案例。",
            "depends_on": [],
        },
        {
            "id": "task_2",
            "agent": "litigation_strategist",
            "instruction_suffix": "制定诉讼策略。",
            "depends_on": ["task_1"],
        },
    ],
    "IP_PROTECTION": [
        {"id": "task_1", "agent": "ip_specialist", "depends_on": []},
    ],
    "REGULATORY_MONITORING": [
        {"id": "task_1", "agent": "regulatory_monitor", "depends_on": []},
    ],
    "TAX_FINANCE": [
        {"id": "task_1", "agent": "tax_compliance", "depends_on": []},
    ],
    "LABOR_HR": [
        {"id": "task_1", "agent": "labor_compliance", "depends_on": []},
    ],
    "EVIDENCE_PROCESSING": [
        {"id": "task_1", "agent": "evidence_analyst", "depends_on": []},
    ],
    "E_SIGNATURE": [
        {"id": "task_1", "agent": "contract_steward", "depends_on": []},
    ],
    "CONTRACT_MANAGEMENT": [
        {"id": "task_1", "agent": "contract_steward", "depends_on": []},
    ],
    "POLICY_DISTRIBUTION": [
        {"id": "task_1", "agent": "labor_compliance", "depends_on": []},
    ],
    "FIND_LAWYER": [
        {"id": "task_1", "agent": "legal_advisor", "depends_on": []},
    ],
    # v3 新增场景路由
    "DEBT_COLLECTION": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析债务催收方案，评估催收路径（协商→律师函→诉讼→执行）。",
            "depends_on": [],
        },
    ],
    "CORPORATE_GOVERNANCE": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析公司治理问题，提供股权/章程/决议方面的法律建议。",
            "depends_on": [],
        },
    ],
    "FAMILY_LAW": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析婚姻家庭法律问题，提供离婚/继承/抚养相关建议。",
            "depends_on": [],
        },
    ],
    "REAL_ESTATE": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析房产法律问题，提供买卖/租赁/纠纷处理建议。",
            "depends_on": [],
        },
    ],
    "CRIMINAL": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析刑事案件情况，提供辩护策略和权益保障建议。注意紧急性评估。",
            "depends_on": [],
        },
    ],
    # v3.1 企业经营管理场景路由
    "INVESTMENT_FINANCING": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析融资/投资事项，审查交易结构、核心条款（估值/对赌/反稀释/退出等）。",
            "depends_on": [],
        },
    ],
    "MA_RESTRUCTURING": [
        {
            "id": "task_1",
            "agent": "due_diligence",
            "instruction_suffix": "对并购目标进行法律尽调分析。",
            "depends_on": [],
        },
        {
            "id": "task_2",
            "agent": "legal_advisor",
            "instruction_suffix": "基于尽调结果，设计并购交易方案和风险应对策略。",
            "depends_on": ["task_1"],
        },
    ],
    "CROSS_BORDER": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析跨境/涉外法律问题，关注适用法律、管辖、出口管制、外汇等合规要求。",
            "depends_on": [],
        },
    ],
    "DATA_COMPLIANCE": [
        {
            "id": "task_1",
            "agent": "regulatory_monitor",
            "instruction_suffix": "评估数据合规状态，对照个保法/GDPR/数据安全法等要求提供合规建议。",
            "depends_on": [],
        },
    ],
    "ANTI_UNFAIR_COMPETITION": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析不正当竞争问题，评估商业秘密保护、竞业限制等法律风险。",
            "depends_on": [],
        },
    ],
    "FRANCHISE_DISTRIBUTION": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析特许经营/经销法律问题，关注合规备案、合同条款、区域保护等。",
            "depends_on": [],
        },
    ],
    "CONSTRUCTION_ENGINEERING": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析建设工程法律问题，关注合同条款、工程款结算、质量责任等。",
            "depends_on": [],
        },
    ],
    "GOVERNMENT_CONTRACTS": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析政府采购/PPP法律问题，关注招投标合规、合同特殊条款、履约要求。",
            "depends_on": [],
        },
    ],
    "BANKRUPTCY_INSOLVENCY": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析破产/清算法律问题，评估程序选择、债权债务、资产处置等。",
            "depends_on": [],
        },
    ],
    "ENVIRONMENTAL_COMPLIANCE": [
        {
            "id": "task_1",
            "agent": "regulatory_monitor",
            "instruction_suffix": "评估环保合规状态，对照环保法/排污许可/碳排放等要求提供建议。",
            "depends_on": [],
        },
    ],
    "ANTI_CORRUPTION": [
        {
            "id": "task_1",
            "agent": "regulatory_monitor",
            "instruction_suffix": "评估反贿赂/反腐败合规体系，对照FCPA/反不正当竞争法等提供建议。",
            "depends_on": [],
        },
    ],
    "PRODUCT_LIABILITY": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析产品责任/消费者权益问题，评估召回义务、赔偿责任、诉讼风险。",
            "depends_on": [],
        },
    ],
    # Harness: 模板请求路由 — 用户只要模板不要AI生成
    "TEMPLATE_REQUEST": [
        {"id": "task_1", "agent": "template_librarian", "depends_on": []},
    ],
    # v4 法律计算路由 — 精确计算器 + 法律分析
    "LEGAL_CALCULATION": [
        {"id": "task_1", "agent": "legal_calculator", "depends_on": []},
    ],
    # v4.1 P0 新增场景路由
    "CONSUMER_PROTECTION": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析消费者维权问题，引用《消费者权益保护法》《产品质量法》，提供投诉/诉讼/行政举报等多渠道维权方案。",
            "depends_on": [],
        },
    ],
    "TRAFFIC_ACCIDENT": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析交通事故责任与赔偿，引用《道路交通安全法》，计算人身/财产损害赔偿，提供保险理赔和诉讼指引。",
            "depends_on": [],
        },
    ],
    "INSURANCE_CLAIM": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析保险理赔纠纷，引用《保险法》，评估保险公司拒赔理由是否合法，提供理赔策略和投诉/诉讼方案。",
            "depends_on": [],
        },
    ],
    "SOCIAL_INSURANCE": [
        {
            "id": "task_1",
            "agent": "labor_compliance",
            "instruction_suffix": "分析社保/公积金问题，引用《社会保险法》《住房公积金管理条例》，提供补缴/投诉/仲裁方案。",
            "depends_on": [],
        },
    ],
    "PROPERTY_MANAGEMENT": [
        {
            "id": "task_1",
            "agent": "legal_advisor",
            "instruction_suffix": "分析物业管理纠纷，引用《民法典》物权编和《物业管理条例》，区分业主和物业公司视角提供解决方案。",
            "depends_on": [],
        },
    ],
}


class CoordinatorAgent(BaseLegalAgent):
    """
    增强版协调调度智能体 (v2)

    优化点：
    1. 不再通过修改 self.system_prompt + _init_agent() 来切换 Prompt
       改为使用 chat(system_prompt_override=...) 参数
    2. 意图识别增加内存缓存（TTL 5分钟），相同输入短时间内复用
    3. 大部分意图使用模板化快速路径，仅 COMPLEX_TASK 调用 LLM 规划 DAG
    """

    # 意图识别缓存 {hash: (result, timestamp)}
    _intent_cache: dict[str, tuple[dict[str, Any], float]] = {}
    INTENT_CACHE_TTL = 300  # 5分钟

    def __init__(self) -> None:
        config = AgentConfig(
            name="协调调度Agent",
            role="协调者",
            description="意图识别、任务编排、结果汇总",
            system_prompt="你是AI 智能助手系统的核心大脑。",
            temperature=0.1,
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理任务入口"""
        analysis_result = await self.analyze_task(task)

        return AgentResponse(
            agent_name=self.name,
            content=analysis_result.get("analysis", "任务规划完成"),
            metadata=analysis_result,
        )

    async def analyze_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        两阶段任务分析：
        1. 意图识别 (Intent Classification) — 带缓存
        2. 路由/规划 (Routing / Planning) — 模板化快速路径优先
        3. 响应策略决策 (Response Strategy) — chat_only / chat_with_a2ui / workspace
        """
        description = task.get("description", "")
        context = task.get("context", {})
        similar_cases = context.get("similar_cases", [])
        intent_hint = context.get("intent_hint")  # 前端正则辅助提示

        # --- Stage 0: 多模态预处理 ---
        files = context.get("files", [])
        processed_files = []
        if files:
            from src.services.multimodal_service import multimodal_service

            logger.info(f"检测到 {len(files)} 个附件，开始多模态预处理...")
            for f_path in files:
                res = await multimodal_service.process_file(f_path, f_path.split("/")[-1])
                processed_files.append(res)
                description += f"\n\n[附件上下文] 文件名: {res['file_name']}, 类型: {res['file_type']}, 摘要: {res.get('summary', '')}"
            context["processed_files"] = processed_files

        logger.info(f"Coordinator 开始分析任务: {description[:50]}...")
        if intent_hint:
            logger.info(f"  辅助意图提示: {intent_hint}")

        # --- Stage 1: 意图识别（预注入 → 极速路径 → 缓存 → LLM 兜底）---
        # 1a) 检查 context 中是否已有预分析的 intent（来自 analyze_and_classify 合并调用）
        pre_intent = context.get("pre_intent")
        pre_confidence = context.get("pre_confidence", 0)
        if pre_intent and pre_confidence >= 0.7:
            intent = pre_intent
            confidence = pre_confidence
            logger.info(f"⚡ 极速意图(预注入): {intent} (置信度: {confidence})")
        else:
            # 1b) 关键词规则引擎：0ms 级别匹配，覆盖 80% 常见场景
            intent_data = self._fast_keyword_intent(description)
            if intent_data and intent_data.get("confidence", 0) >= 0.8:
                intent = intent_data["intent"]
                confidence = intent_data["confidence"]
                logger.info(f"⚡ 极速意图(关键词): {intent} (置信度: {confidence})")
            else:
                # 1c) LLM 意图分类（带缓存，仅复杂/模糊消息）
                intent_data = await self._classify_intent(description)
                intent = intent_data.get("intent", "COMPLEX_TASK")
                confidence = intent_data.get("confidence", 0.0)
                logger.info(f"意图识别结果(LLM): {intent} (置信度: {confidence})")

        hint_mapping = {
            "find_lawyer": "FIND_LAWYER",
            "review_contract": "CONTRACT_REVIEW",
            "draft_document": "DOCUMENT_DRAFTING",
            "risk_assessment": "REGULATORY_MONITORING",
            "due_diligence": "DUE_DILIGENCE",
            "legal_consultation": "QA_CONSULTATION",
        }
        hinted_intent = hint_mapping.get(intent_hint)
        if hinted_intent and intent != hinted_intent and confidence < 0.93:
            logger.info(f"使用前端意图提示覆盖识别结果: {intent} -> {hinted_intent}")
            intent = hinted_intent
            confidence = max(confidence, 0.9)

        # --- Stage 2: 动态路由与规划 ---

        # 模板化快速路径：大部分单一意图无需 LLM DAG 规划
        if intent in FAST_PATH_ROUTES and intent != "COMPLEX_TASK":
            result = self._generate_template_plan(description, intent)
        else:
            # Complex Path: 仅 COMPLEX_TASK 使用 LLM 生成完整 DAG
            result = await self._generate_dag_plan(description, context, similar_cases, intent)

        # --- Stage 3: 响应策略决策 ---
        result["response_strategy"] = self._decide_response_strategy(intent, description, context)

        # --- Stage 4: 场景 A2UI 配置（告诉 Agent 推荐嵌入什么卡片） ---
        result["scene_a2ui_config"] = self.get_scene_a2ui_config(intent)

        return result

    def _decide_response_strategy(
        self, intent: str, description: str, context: dict[str, Any]
    ) -> str:
        """
        渐进式响应策略决策（千问风格 v3 — 模式感知增强版意图深化）：

        核心理念：先对话理解需求 → 逐步升级交互复杂度
        新增：前端 mode 药丸（deep_analysis/contract/document/research）影响策略升级阈值

        策略等级（递进）：
        - 'chat_only': 纯文本对话回复（简单问答、概念解释、初次需求了解）
        - 'chat_with_a2ui': 对话 + 一次性 A2UI 卡片（简单推荐、状态展示）
        - 'chat_with_streaming_a2ui': 对话 + 流式 A2UI 卡片（千问购物模式：逐个生长的推荐卡片）
        - 'workspace': 需要右侧工作台（文档编辑、复杂报告、分析仪表盘等）

        渐进式深化决策树：
        1. intent_clarity = "clear" | "partial" | "vague"
        2. task_complexity = "simple" | "medium" | "complex"
        3. need_structured_ui = True | False
        4. **NEW**: frontend_mode 影响升级倾向
        """
        has_files = bool(context.get("files") or context.get("processed_files"))
        conversation_turns = context.get("conversation_turns", 0)
        has_sufficient_info = context.get("has_sufficient_info", False)
        frontend_mode = context.get("mode", "chat")  # 前端功能模式药丸

        # --- 意图清晰度评估 ---
        desc_len = len(description)
        _clarity_keywords_strong = [
            "审查",
            "起草",
            "尽职调查",
            "风险评估",
            "诉讼策略",
            "签约",
            "归档",
        ]
        _clarity_keywords_partial = ["合同", "律师", "纠纷", "赔偿", "员工", "税务", "专利"]

        has_strong_keyword = any(kw in description for kw in _clarity_keywords_strong)
        has_partial_keyword = any(kw in description for kw in _clarity_keywords_partial)

        if has_strong_keyword and desc_len > 30:
            intent_clarity = "clear"
        elif has_partial_keyword or desc_len > 20:
            intent_clarity = "partial"
        else:
            intent_clarity = "vague"

        # 补充信息充分度（多轮对话修正）
        if conversation_turns > 1 or has_sufficient_info:
            intent_clarity = "clear"
        elif conversation_turns == 1 and intent_clarity == "vague":
            intent_clarity = "partial"

        # --- 模式加成：非 chat 模式降低升级门槛 ---
        # 用户主动选择了专业模式，说明意图较明确，提升清晰度评级
        if frontend_mode != "chat" and intent_clarity == "vague":
            intent_clarity = "partial"
        if frontend_mode != "chat" and intent_clarity == "partial":
            intent_clarity = "clear"

        # --- 决策逻辑 ---

        # === 千问式场景映射：渐进式意图深化 ===

        # 有附件时直接进入工作台
        if has_files:
            return "workspace"

        # === 模式优先路由：前端模式药丸覆盖默认策略 ===

        # 合同模式 → 倾向合同类操作
        if frontend_mode == "contract":
            if intent in {"CONTRACT_REVIEW", "CONTRACT_MANAGEMENT"}:
                return "workspace" if has_files else "chat_with_streaming_a2ui"
            # 合同模式下其他意图也倾向 A2UI
            if intent_clarity in ("clear", "partial"):
                return "chat_with_streaming_a2ui"

        # 文书模式 → 倾向工作台
        if frontend_mode == "document":
            if intent in {
                "DOCUMENT_DRAFTING",
                "E_SIGNATURE",
                "EVIDENCE_PROCESSING",
                "CONTRACT_REVIEW",
                "CONTRACT_MANAGEMENT",
            }:
                return "workspace"
            # 文书模式下高清晰度 → 直接开工作台
            if intent_clarity == "clear":
                return "workspace"
            return "chat_with_a2ui"

        # 深度分析模式 → 倾向流式 A2UI 展示分析结果
        if frontend_mode == "deep_analysis":
            if has_files:
                return "workspace"
            if intent_clarity == "clear":
                return "chat_with_streaming_a2ui"
            return "chat_with_a2ui"

        # 研究模式 → 倾向流式 A2UI 展示搜索/研究结果
        if frontend_mode == "research":
            if intent_clarity in ("clear", "partial"):
                return "chat_with_streaming_a2ui"
            return "chat_with_a2ui"

        # === 默认（chat 模式）：渐进式策略 ===

        # 场景 1: 简单问答 → 渐进式深化
        # 千问模式：简单问答在多轮对话后也能升级（如"找律师"→补充信息→推荐卡片）
        if intent == "QA_CONSULTATION":
            if conversation_turns >= 2 and intent_clarity == "clear":
                # 多轮对话且信息充分：升级为流式 A2UI（推荐律师、相关法规等）
                return "chat_with_streaming_a2ui"
            if conversation_turns >= 1 and intent_clarity in ("clear", "partial"):
                # 已有一轮补充：提供一次性 A2UI 卡片辅助
                return "chat_with_a2ui"
            return "chat_only"

        # 场景 2: 文档编辑类 → 始终工作台
        if intent in {"DOCUMENT_DRAFTING", "E_SIGNATURE", "EVIDENCE_PROCESSING"}:
            return "workspace"

        # 场景 3: 合同审查 → 需要附件才开工作台，否则先对话
        if intent == "CONTRACT_REVIEW":
            if has_files:
                return "workspace"
            # 无附件但意图清晰 → 对话引导上传
            return "chat_only"

        # 场景 4: 合同管理 → 工作台
        if intent == "CONTRACT_MANAGEMENT":
            return "workspace"

        # 场景 5: 找律师/尽调/诉讼等 → 千问购物式渐进
        #   vague  → chat_only（先对话澄清需求）
        #   partial → chat_only（继续对话补充信息）
        #   clear  → chat_with_streaming_a2ui（流式推送卡片：律师推荐、风险评估等）
        if intent in {
            "FIND_LAWYER",
            "DUE_DILIGENCE",
            "LITIGATION_STRATEGY",
            "IP_PROTECTION",
            "REGULATORY_MONITORING",
            "TAX_FINANCE",
            "LABOR_HR",
            "POLICY_DISTRIBUTION",
        }:
            if intent_clarity == "clear":
                return "chat_with_streaming_a2ui"
            if intent_clarity == "partial" and conversation_turns > 0:
                return "chat_with_a2ui"
            return "chat_only"  # 信息不足，先对话理解

        # 场景 6: 复杂任务 → 根据意图清晰度和信息充分度决定
        if intent == "COMPLEX_TASK":
            if has_files:
                return "workspace"
            if intent_clarity == "clear":
                # 复杂但信息充分 → 流式卡片 + 可能需要工作台
                return "chat_with_streaming_a2ui"
            if intent_clarity == "partial":
                return "chat_with_a2ui"
            return "chat_only"

        # 默认：对话优先
        return "chat_only"

    def get_scene_a2ui_config(self, intent: str) -> dict[str, Any]:
        """
        千问式场景映射 v2：为不同意图返回推荐的 A2UI 组件配置

        告诉 Agent 在回复中应当嵌入什么类型的 A2UI 卡片。

        增强字段：
        - suggested_cards: 推荐的卡片类型列表
        - layout: 卡片布局方式（vertical / horizontal-scroll）
        - streaming_hint: 建议是否使用流式推送（true = 逐个生长）
        - primary_card: 优先展示的卡片（用于移动端首屏）
        - description: 场景说明（给 Agent 的提示）
        """
        scene_map = {
            "DUE_DILIGENCE": {
                "suggested_cards": [
                    "risk-assessment",
                    "risk-indicator",
                    "detail-list",
                    "case-progress",
                ],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "risk-assessment",
                "description": "尽职调查结果以风险雷达图+风险仪表盘+详情列表展示，流式逐步推送",
            },
            "LITIGATION_STRATEGY": {
                "suggested_cards": [
                    "risk-assessment",
                    "case-progress",
                    "fee-estimate",
                    "recommendation-card",
                ],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "risk-assessment",
                "description": "诉讼策略以风险评估雷达+案件进度+费用估算+律师推荐展示，流式逐步推送",
            },
            "CONTRACT_REVIEW": {
                "suggested_cards": ["contract-compare", "risk-assessment", "risk-indicator"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "contract-compare",
                "description": "合同审查结果以条款对比+风险雷达图+风险指标展示",
            },
            "DOCUMENT_DRAFTING": {
                "suggested_cards": ["case-progress", "status-card"],
                "layout": "vertical",
                "streaming_hint": False,
                "primary_card": "case-progress",
                "description": "文书起草进度以案件进度时间线+状态卡展示",
            },
            "TAX_FINANCE": {
                "suggested_cards": ["fee-estimate", "detail-list", "risk-indicator"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "fee-estimate",
                "description": "财税咨询以费用估算+详情列表+风险指标展示",
            },
            "LABOR_HR": {
                "suggested_cards": ["risk-assessment", "detail-list", "recommendation-card"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "detail-list",
                "description": "劳动人事以风险评估+详情列表+推荐方案展示",
            },
            "IP_PROTECTION": {
                "suggested_cards": ["case-progress", "risk-assessment", "detail-list"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "case-progress",
                "description": "知识产权保护以案件进度+风险评估+详情列表展示",
            },
            "REGULATORY_MONITORING": {
                "suggested_cards": ["risk-assessment", "detail-list", "info-banner", "checklist"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "risk-assessment",
                "description": "合规监管以风险评估雷达+详情+警示横幅+合规检查表展示",
            },
            "LEGAL_CALCULATION": {
                "suggested_cards": [
                    "fee-estimate",
                    "detail-list",
                    "recommendation-card",
                    "risk-indicator",
                ],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "fee-estimate",
                "description": "法务分析以费用明细+法律分析+风险评估+操作方案展示，支持咨询与计算双模式",
            },
            "COMPLEX_TASK": {
                "suggested_cards": ["case-progress", "risk-assessment", "detail-list"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "case-progress",
                "description": "复杂任务以案件进度+风险评估+详情展示，流式推送",
            },
            "FIND_LAWYER": {
                "suggested_cards": ["lawyer-card", "recommendation-card", "horizontal-scroll"],
                "layout": "horizontal-scroll",
                "streaming_hint": True,
                "primary_card": "lawyer-card",
                "description": "找律师以律师推荐卡片横滑列表展示，支持联系、查看详情、AI智能匹配",
            },
            "QA_CONSULTATION": {
                "suggested_cards": ["recommendation-card", "detail-list"],
                "layout": "horizontal-scroll",
                "streaming_hint": True,
                "primary_card": "recommendation-card",
                "description": "问答咨询在多轮对话深化后以推荐卡片+详情列表展示（如律师推荐、法规速览）",
            },
            "E_SIGNATURE": {
                "suggested_cards": ["case-progress", "status-card"],
                "layout": "vertical",
                "streaming_hint": False,
                "primary_card": "case-progress",
                "description": "电子签约流程以进度时间线+状态卡展示",
            },
            "CONTRACT_MANAGEMENT": {
                "suggested_cards": ["case-progress", "detail-list", "status-card"],
                "layout": "vertical",
                "streaming_hint": False,
                "primary_card": "case-progress",
                "description": "合同管理以进度时间线+详情列表+状态卡展示",
            },
            "EVIDENCE_PROCESSING": {
                "suggested_cards": ["detail-list", "risk-assessment"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "detail-list",
                "description": "证据分析以详情列表+风险评估展示",
            },
            "POLICY_DISTRIBUTION": {
                "suggested_cards": ["case-progress", "detail-list"],
                "layout": "vertical",
                "streaming_hint": False,
                "primary_card": "case-progress",
                "description": "规章制度发布以进度时间线+详情列表展示",
            },
        }
        return scene_map.get(
            intent,
            {
                "suggested_cards": [],
                "layout": "vertical",
                "streaming_hint": False,
                "primary_card": None,
                "description": "默认纯文本展示",
            },
        )

    # ========== 极速关键词意图匹配（0ms 级别，跳过 LLM）==========

    # 关键词 → 意图映射表（按优先级排列，越靠前越优先）
    # 注意：关键词仅匹配用户输入的前 200 字符（即用户实际问题），避免合同正文干扰
    _KEYWORD_INTENT_RULES = [
        # (关键词列表, 意图, 置信度)
        # Harness: 模板请求优先匹配（在生成类意图之前，避免"合同模板"匹配到"合同审查"）
        (
            [
                "合同模板",
                "模板下载",
                "下载模板",
                "给我模板",
                "模板库",
                "范本下载",
                "下载范本",
                "文书模板",
                "协议模板",
                "样本下载",
            ],
            "TEMPLATE_REQUEST",
            0.93,
        ),
        (
            [
                "找律师",
                "推荐律师",
                "帮我找律师",
                "律师推荐",
                "委托律师",
                "请律师",
                "聘请律师",
                "请个律师",
                "找个律师",
            ],
            "FIND_LAWYER",
            0.92,
        ),
        (
            [
                "审查合同",
                "合同审查",
                "审合同",
                "审查这份",
                "审查一下",
                "条款审核",
                "合同风险",
                "帮我审查",
            ],
            "CONTRACT_REVIEW",
            0.92,
        ),
        (["电子签", "发起签约", "电子签章", "电子签约", "在线签署"], "E_SIGNATURE", 0.92),
        (["归档", "合同到期", "履约提醒", "合同管理", "合同状态"], "CONTRACT_MANAGEMENT", 0.90),
        (["发布制度", "签收", "全员通知", "公告", "员工手册发布"], "POLICY_DISTRIBUTION", 0.90),
        (
            ["起草", "草拟", "写一份", "拟一份", "律师函", "法律文书", "法律意见书"],
            "DOCUMENT_DRAFTING",
            0.90,
        ),
        (
            [
                "尽职调查",
                "尽调",
                "背景调查",
                "企业调查",
                "查公司",
                "调查公司",
                "查一下公司",
                "看看公司",
                "公司怎么样",
                "工商信息",
                "股权结构",
                "诉讼记录",
                "信用记录",
                "供应商靠不靠谱",
                "合作方风险",
                "交易对手背景",
            ],
            "DUE_DILIGENCE",
            0.90,
        ),
        (["诉讼策略", "起诉", "胜诉", "败诉", "庭审", "反诉", "仲裁"], "LITIGATION_STRATEGY", 0.88),
        (
            [
                "风险评估",
                "合规检查",
                "合规审查",
                "合规风险",
                "合规自检",
                "合规自查",
                "内审",
                "合规体检",
                "内部审查",
                "制度审计",
            ],
            "REGULATORY_MONITORING",
            0.88,
        ),
        (["专利", "商标", "侵权", "知识产权", "版权"], "IP_PROTECTION", 0.88),
        # v4 法律计算场景（优先于 LABOR_HR，"赔多少""赔偿金""诉讼费""时效"等触发精确计算）
        (
            [
                "赔多少",
                "赔偿金",
                "补偿金",
                "N+1",
                "2N",
                "经济补偿",
                "赔偿计算",
                "补偿计算",
                "怎么算",
                "赔偿标准",
            ],
            "LEGAL_CALCULATION",
            0.92,
        ),
        (
            ["诉讼费", "打官司多少钱", "打官司费用", "起诉费", "受理费", "诉讼成本"],
            "LEGAL_CALCULATION",
            0.92,
        ),
        (
            ["时效", "诉讼时效", "过期", "还能起诉", "超过时效", "仲裁时效", "过了时效"],
            "LEGAL_CALCULATION",
            0.90,
        ),
        (["加班费", "加班工资", "加班怎么算", "加班补偿"], "LEGAL_CALCULATION", 0.92),
        (["工伤赔偿", "伤残赔偿", "伤残等级", "工伤补偿"], "LEGAL_CALCULATION", 0.92),
        (
            [
                "辞退",
                "劳动合同",
                "劳动仲裁",
                "工资拖欠",
                "员工",
                "入职",
                "试用期",
                "社保",
                "劳动争议",
                "劳动法",
                "工伤",
            ],
            "LABOR_HR",
            0.88,
        ),
        (["发票", "报销", "税务", "财税", "避税", "税收", "股权转让"], "TAX_FINANCE", 0.88),
        (["录音", "证据", "鉴定", "证据链"], "EVIDENCE_PROCESSING", 0.88),
        # v3 新增场景
        (
            ["欠钱", "欠款", "催收", "不还钱", "欠我", "讨债", "追债", "催款"],
            "DEBT_COLLECTION",
            0.90,
        ),
        (
            [
                "股东纠纷",
                "股权架构",
                "公司章程",
                "股东僵局",
                "增资",
                "减资",
                "股权设计",
                "公司治理",
            ],
            "CORPORATE_GOVERNANCE",
            0.88,
        ),
        (
            ["离婚", "分居", "抚养权", "财产分割", "家暴", "遗产", "继承", "遗嘱"],
            "FAMILY_LAW",
            0.90,
        ),
        (
            ["买房", "卖房", "租房纠纷", "物业纠纷", "拆迁", "房屋质量", "交房", "房产"],
            "REAL_ESTATE",
            0.88,
        ),
        (["刑事", "拘留", "逮捕", "取保候审", "传唤", "犯罪", "嫌疑人", "辩护"], "CRIMINAL", 0.92),
        # v3.1 企业经营管理场景
        (
            [
                "融资",
                "A轮",
                "B轮",
                "C轮",
                "天使轮",
                "投资协议",
                "Term Sheet",
                "估值",
                "对赌",
                "股权融资",
            ],
            "INVESTMENT_FINANCING",
            0.90,
        ),
        (["并购", "收购", "兼并", "重组", "资产剥离", "MBO", "企业整合"], "MA_RESTRUCTURING", 0.90),
        (
            ["跨境", "涉外", "国际贸易", "进出口", "出口管制", "外商投资", "对外投资", "FCPA"],
            "CROSS_BORDER",
            0.88,
        ),
        (
            [
                "数据合规",
                "个人信息保护",
                "PIPL",
                "GDPR",
                "数据泄露",
                "隐私政策",
                "数据出境",
                "等保",
            ],
            "DATA_COMPLIANCE",
            0.90,
        ),
        (
            ["商业秘密", "不正当竞争", "仿冒", "虚假宣传", "商业诋毁", "窃取客户"],
            "ANTI_UNFAIR_COMPETITION",
            0.88,
        ),
        (
            ["特许经营", "加盟", "经销商", "代理商", "品牌授权", "窜货"],
            "FRANCHISE_DISTRIBUTION",
            0.88,
        ),
        (
            ["建设工程", "工程款", "施工合同", "分包", "转包", "挂靠", "竣工验收", "工程结算"],
            "CONSTRUCTION_ENGINEERING",
            0.88,
        ),
        (["政府采购", "投标", "中标", "PPP", "政府合同"], "GOVERNMENT_CONTRACTS", 0.88),
        (
            ["破产", "清算", "破产重整", "债务重组", "资不抵债", "破产申请"],
            "BANKRUPTCY_INSOLVENCY",
            0.90,
        ),
        (
            ["环保", "环评", "排污", "碳排放", "碳交易", "环境污染", "环保处罚"],
            "ENVIRONMENTAL_COMPLIANCE",
            0.88,
        ),
        (["反贿赂", "反腐败", "商业贿赂", "回扣", "FCPA合规"], "ANTI_CORRUPTION", 0.88),
        (
            ["产品责任", "产品召回", "消费者投诉", "食品安全", "产品质量", "消费者维权"],
            "PRODUCT_LIABILITY",
            0.88,
        ),
        # v4.1 P0 新增场景
        (
            [
                "消费维权",
                "退款",
                "假货",
                "商品质量",
                "消费者",
                "投诉商家",
                "315",
                "欺诈消费",
                "虚假宣传",
                "预付卡",
                "充值不退",
            ],
            "CONSUMER_PROTECTION",
            0.90,
        ),
        (
            ["交通事故", "车祸", "追尾", "撞车", "刮蹭", "肇事", "交通赔偿", "交通责任"],
            "TRAFFIC_ACCIDENT",
            0.92,
        ),
        (["保险理赔", "拒赔", "保险不赔", "保险纠纷", "定损", "理赔"], "INSURANCE_CLAIM", 0.90),
        (
            [
                "社保",
                "公积金",
                "不交社保",
                "没交社保",
                "断缴",
                "补缴",
                "社保转移",
                "生育津贴",
                "养老金",
            ],
            "SOCIAL_INSURANCE",
            0.90,
        ),
        (
            ["物业", "物业费", "业委会", "物业纠纷", "停车位", "维修基金", "小区"],
            "PROPERTY_MANAGEMENT",
            0.88,
        ),
        (["新规", "政策", "法规解读", "监管"], "REGULATORY_MONITORING", 0.85),
        (
            [
                "查法条",
                "搜案例",
                "法规查询",
                "法律检索",
                "查找法规",
                "相关判例",
                "法条检索",
                "案例检索",
            ],
            "QA_CONSULTATION",
            0.85,
        ),
    ]

    async def analyze_and_classify(
        self,
        description: str,
        has_attachments: bool = False,
        llm_config: Any | None = None,
        user_profile_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        合并需求分析 + 意图识别（v2 — 场景模板驱动 + 置信度门控）。

        先尝试关键词快速路径确定意图，再用场景模板评估信息完整度。
        仅在关键词未命中时才调用 LLM。
        返回格式兼容原 requirement_analyst.analyze_requirement() 的结果，
        同时额外包含 intent、confidence、filled_slots 等字段。
        """
        pre_filled = (user_profile_context or {}).get("default_context", {})

        # 快速路径：关键词命中 → 确定意图 → 场景模板评估完整度
        keyword_result = self._fast_keyword_intent(description)
        if keyword_result and keyword_result.get("confidence", 0) >= 0.8:
            intent = keyword_result["intent"]
            logger.info(f"⚡ 合并分析-关键词命中: {intent}")

            # 用场景模板评估信息完整度（纯规则 < 1ms，不再直接标记 is_complete=True）
            completeness = assess_completeness(
                description,
                intent,
                has_attachments=has_attachments,
                pre_filled_context=pre_filled,
            )

            return {
                "is_complete": completeness["is_complete"],
                "completeness_score": completeness["score"],
                "summary": description[:100],
                "complexity": "simple" if intent == "QA_CONSULTATION" else "moderate",
                "intent": intent,
                "confidence": keyword_result["confidence"],
                "guidance_questions": completeness["questions"],
                "missing_elements": [s["label"] for s in completeness["missing_slots"]],
                "filled_slots": completeness["filled_slots"],
                "context_summary": build_context_summary(completeness["filled_slots"]),
                "suggested_agents": [
                    FAST_PATH_ROUTES.get(intent, [{}])[0].get("agent", "legal_advisor")
                ],
            }

        # LLM 合并调用（缓存检查）
        cache_key = hashlib.md5(f"merged:{description}".encode()).hexdigest()
        if cache_key in self._intent_cache:
            cached_result, cached_time = self._intent_cache[cache_key]
            if time.time() - cached_time < self.INTENT_CACHE_TTL:
                logger.debug(f"合并分析命中缓存: {cached_result.get('intent')}")
                return cached_result

        attachment_hint = "[注意：用户已上传附件文件]" if has_attachments else ""

        # 尝试用关键词预判意图，为 LLM 注入对应场景模板上下文（Fix 7）
        _hint_result = self._fast_keyword_intent(description)
        _hint_intent = (
            _hint_result["intent"]
            if _hint_result and _hint_result.get("confidence", 0) >= 0.5
            else ""
        )
        template_context_hint = (
            get_template_context_for_llm(_hint_intent, description) if _hint_intent else ""
        )

        merged_prompt = load_prompt(
            "coordinator/merged_intent_analysis.txt",
            fallback="你是一位专业的法务意图识别与需求分析师。",
            attachment_hint=attachment_hint,
            description=description,
            template_context=template_context_hint,
        )

        merged_system = load_prompt(
            "coordinator/merged_intent_system.txt",
            fallback="你是AI 智能助手系统的意图识别与需求分析专家。请精准分析并输出JSON。",
        )

        try:
            response_text = await self.chat(
                merged_prompt,
                system_prompt_override=merged_system,
                max_tokens=512,
                llm_config=llm_config,
            )
            result = self._parse_json(response_text)

            if result:
                # 确保必需字段
                result.setdefault("intent", "QA_CONSULTATION")
                result.setdefault("confidence", 0.7)
                result.setdefault("summary", description[:100])
                result.setdefault("complexity", "simple")
                result.setdefault("suggested_agents", ["legal_advisor"])

                # 用场景模板对 LLM 返回结果做二次校验/增强
                llm_intent = result["intent"]
                completeness = assess_completeness(
                    description,
                    llm_intent,
                    has_attachments=has_attachments,
                    pre_filled_context=pre_filled,
                )

                # 场景模板的评估与 LLM 评估取交集（更严格）
                llm_complete = result.get("is_complete", True)
                template_complete = completeness["is_complete"]
                result["is_complete"] = llm_complete and template_complete
                result["completeness_score"] = min(
                    result.get("completeness_score", 0.8),
                    completeness["score"],
                )

                # 合并追问问题：LLM 生成的 + 场景模板的（去重）
                llm_questions = result.get("guidance_questions", [])
                template_questions = completeness["questions"]
                existing_purposes = {
                    q.get("purpose", "") for q in llm_questions if isinstance(q, dict)
                }
                for tq in template_questions:
                    if tq.get("purpose", "") not in existing_purposes:
                        llm_questions.append(tq)
                result["guidance_questions"] = llm_questions[:3]  # 最多 3 个

                # 补充缺失信息列表
                result["missing_elements"] = result.get("missing_elements", []) or [
                    s["label"] for s in completeness["missing_slots"]
                ]
                result["filled_slots"] = completeness["filled_slots"]
                result["context_summary"] = build_context_summary(completeness["filled_slots"])

                # 写入缓存
                self._intent_cache[cache_key] = (result, time.time())
                self._cleanup_intent_cache()

                logger.info(
                    f"合并分析(LLM+模板): intent={result['intent']}, "
                    f"complete={result['is_complete']}, score={result['completeness_score']}, "
                    f"complexity={result['complexity']}"
                )
                return result
        except Exception as e:
            logger.warning(f"合并分析失败，降级到分离模式: {e}")

        # 降级：返回默认值
        return {
            "is_complete": True,
            "completeness_score": 0.8,
            "summary": description[:100],
            "complexity": "simple",
            "intent": "QA_CONSULTATION",
            "confidence": 0.5,
            "guidance_questions": [],
            "missing_elements": [],
            "suggested_agents": ["legal_advisor"],
        }

    def _fast_keyword_intent(self, description: str) -> dict[str, Any] | None:
        """
        基于关键词的极速意图匹配（无 LLM 调用，< 1ms）。

        覆盖 80% 的常见法务场景，仅在匹配置信度 >= 0.8 时使用。
        仅匹配前 200 字符（用户实际问题），避免合同/文书正文中的关键词造成误匹配。
        """
        # 只取前 200 字符进行关键词匹配，防止合同正文中的"签署""签字"等通用词干扰
        desc_lower = description[:200].lower()
        for keywords, intent, confidence in self._KEYWORD_INTENT_RULES:
            matched = sum(1 for kw in keywords if kw in desc_lower)
            if matched >= 1:
                # 多关键词命中时提升置信度
                boost = min(0.05 * (matched - 1), 0.08)
                return {
                    "intent": intent,
                    "confidence": min(confidence + boost, 0.99),
                    "reasoning": f"关键词匹配: {[kw for kw in keywords if kw in desc_lower]}",
                }
        return None

    async def _classify_intent(self, description: str) -> dict[str, Any]:
        """
        调用 LLM 进行意图分类（带内存缓存）

        优化：相同输入在 TTL 内直接返回缓存结果
        """
        # 计算缓存 Key
        cache_key = hashlib.md5(description.encode()).hexdigest()

        # 检查缓存
        if cache_key in self._intent_cache:
            cached_result, cached_time = self._intent_cache[cache_key]
            if time.time() - cached_time < self.INTENT_CACHE_TTL:
                logger.debug(f"意图识别命中缓存: {cached_result.get('intent')}")
                return cached_result

        try:
            prompt = f"用户输入：{description}\n\n请分析意图（只输出JSON）："

            # 使用 system_prompt_override + max_tokens 限制，加速意图分类响应
            response_text = await self.chat(
                prompt,
                system_prompt_override=load_prompt(
                    "coordinator/intent_classification.txt", fallback=_FALLBACK_INTENT_PROMPT
                ),
                max_tokens=256,  # 意图分类只需要短 JSON，限制输出长度加速响应
            )

            result = self._parse_json(response_text)

            # 写入缓存
            if result:
                self._intent_cache[cache_key] = (result, time.time())
                # 清理过期缓存（防止内存泄漏）
                self._cleanup_intent_cache()

            return result

        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            return {"intent": "COMPLEX_TASK", "confidence": 0.0}

    def _cleanup_intent_cache(self) -> None:
        """清理过期的意图缓存条目"""
        now = time.time()
        expired_keys = [
            k for k, (_, t) in self._intent_cache.items() if now - t > self.INTENT_CACHE_TTL
        ]
        for k in expired_keys:
            del self._intent_cache[k]

    def _generate_template_plan(self, description: str, intent: str) -> dict[str, Any]:
        """
        基于模板生成快速路径计划（无需 LLM 调用）

        大幅减少 LLM 调用次数，适用于大部分单一意图任务。
        """
        template = FAST_PATH_ROUTES.get(intent, [])

        plan = []
        for step in template:
            task_item = {
                "id": step["id"],
                "agent": step["agent"],
                "instruction": description + step.get("instruction_suffix", ""),
                "depends_on": step.get("depends_on", []),
            }
            plan.append(task_item)

        return {
            "analysis": f"识别为 {intent}，使用模板化快速路径。",
            "intent": intent,
            "plan": plan,
            "reasoning": f"基于{INTENT_LABELS.get(intent, intent)}场景模板快速规划",
            "priority": "normal",
            "total_steps": len(plan),
        }

    async def _generate_dag_plan(
        self,
        description: str,
        context: dict[str, Any],
        similar_cases: list[dict[str, Any]],
        intent: str,
    ) -> dict[str, Any]:
        """生成 DAG 计划（仅用于 COMPLEX_TASK）"""

        # 构建历史经验上下文文本
        similar_cases_text = "无相关历史经验"
        if similar_cases:
            cases_str = []
            for i, case in enumerate(similar_cases[:2]):
                cases_str.append(
                    f"案例 {i + 1}:\n- 任务: {case.get('task')}\n"
                    f"- 之前的计划: {json.dumps(case.get('plan'), ensure_ascii=False)}"
                )
            similar_cases_text = "\n\n".join(cases_str)
            logger.info("已注入历史经验上下文用于规划")

        final_prompt_sys = load_prompt(
            "coordinator/task_planning.txt",
            fallback=_FALLBACK_COORDINATOR_PROMPT,
            similar_cases_context=similar_cases_text,
        )
        user_prompt = (
            f"需求描述：{description}\n识别意图：{intent}\n上下文信息：{str(context)[:500]}"
        )

        try:
            # 使用 system_prompt_override 而不是修改实例状态 + 重建客户端
            response_text = await self.chat(user_prompt, system_prompt_override=final_prompt_sys)

            plan_data = self._parse_json(response_text)
            plan_data["intent"] = intent
            return plan_data

        except Exception as e:
            logger.error(f"DAG 规划失败: {e}")
            return await self._fallback_analysis(description)

    async def _fallback_analysis(self, description: str) -> dict[str, Any]:
        """兜底规划（规则引擎）"""
        agents = ["legal_advisor"]

        if "合同" in description:
            agents = ["contract_reviewer"]
        elif "尽调" in description:
            agents = ["due_diligence"]
        elif "诉讼" in description or "仲裁" in description:
            agents = ["litigation_strategist"]
        elif (
            "知识产权" in description
            or "专利" in description
            or "商标" in description
            or "侵权" in description
        ):
            agents = ["ip_specialist"]
        elif "监管" in description or "新规" in description or "政策" in description:
            agents = ["regulatory_monitor"]
        elif "税" in description or "财务" in description or "发票" in description:
            agents = ["tax_compliance"]
        elif (
            "员工" in description
            or "辞退" in description
            or "劳动" in description
            or "入职" in description
        ):
            agents = ["labor_compliance"]
        elif (
            "证据" in description
            or "录音" in description
            or "扫描" in description
            or "图片" in description
        ):
            agents = ["evidence_analyst"]
        elif "签约" in description or "签字" in description or "盖章" in description:
            agents = ["contract_steward"]
        elif "归档" in description or "提醒" in description or "到期" in description:
            agents = ["contract_steward"]
        elif (
            "制度" in description
            or "公告" in description
            or "手册" in description
            or "通知" in description
        ):
            agents = ["labor_compliance"]

        plan = [{"id": "task_1", "agent": agents[0], "instruction": description, "depends_on": []}]

        return {
            "analysis": "规则引擎兜底规划",
            "plan": plan,
            "intent": "UNKNOWN",
            "reasoning": "Fallback",
            "total_steps": 1,
        }

    def _parse_json(self, text: str) -> dict[str, Any]:
        """辅助 JSON 解析"""
        if not text:
            return {}
        try:
            return cast(dict[str, Any], json.loads(text))
        except (json.JSONDecodeError, TypeError):
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match:
                try:
                    return cast(dict[str, Any], json.loads(match.group(1)))
                except (json.JSONDecodeError, TypeError):
                    pass
        return {}

    async def aggregate_results(self, results: list[AgentResponse]) -> dict[str, Any]:
        from datetime import datetime

        summary = "任务执行完成。\n\n"
        review_result: dict[str, Any] = {}
        investigation: dict[str, Any] = {}
        verification: dict[str, Any] = {}

        for r in results:
            if not isinstance(r, AgentResponse):
                continue

            summary += f"### {r.agent_name}\n{r.content}\n\n"
            metadata = r.metadata if isinstance(r.metadata, dict) else {}

            if not metadata and isinstance(r.actions, list):
                for action in r.actions:
                    if isinstance(action, dict) and isinstance(action.get("data"), dict):
                        metadata = action["data"]
                        break

            if metadata.get("summary") or metadata.get("risks") or metadata.get("key_risks"):
                review_result = self._merge_contract_review_result(review_result, metadata)

            if any(
                key in metadata
                for key in ("contract_type", "parties", "focus_areas", "missing_elements")
            ):
                investigation = self._merge_nested_result(investigation, metadata)

            if any(
                key in metadata
                for key in (
                    "quality_score",
                    "confidence_level",
                    "verification_results",
                    "missed_areas",
                )
            ):
                verification = self._merge_nested_result(verification, metadata)

        result = {
            "summary": review_result.get("summary") or summary,
            "agent_count": len(results),
            "generated_at": datetime.now().isoformat(),
        }

        if review_result:
            result.update(review_result)

        if investigation:
            result["investigation"] = investigation

        if verification:
            result["verification"] = verification

        return result

    def _merge_contract_review_result(
        self, current: dict[str, Any], incoming: dict[str, Any]
    ) -> dict[str, Any]:
        merged = dict(current)
        risks = incoming.get("risks")
        key_risks = incoming.get("key_risks")

        if not risks and isinstance(key_risks, list):
            risks = key_risks
        if not key_risks and isinstance(risks, list):
            key_risks = risks

        scalar_fields = ("summary", "risk_level", "risk_score")
        collection_fields = {
            "risks": risks,
            "key_risks": key_risks,
            "suggestions": incoming.get("suggestions"),
            "missing_clauses": incoming.get("missing_clauses"),
        }

        for field in scalar_fields:
            value = incoming.get(field)
            if value not in (None, "", []):
                merged[field] = value

        for field, value in collection_fields.items():
            if isinstance(value, list):
                merged[field] = value

        key_terms = incoming.get("key_terms")
        if isinstance(key_terms, dict):
            merged["key_terms"] = key_terms

        return merged

    def _merge_nested_result(
        self, current: dict[str, Any], incoming: dict[str, Any]
    ) -> dict[str, Any]:
        merged = dict(current)
        for key, value in incoming.items():
            if value not in (None, "", [], {}):
                merged[key] = value
        return merged

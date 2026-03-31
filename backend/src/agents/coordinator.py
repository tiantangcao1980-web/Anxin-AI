"""
协调调度智能体 (v2 - 性能优化版)

优化点：
1. 消除 _init_agent() 重复调用 — 使用 system_prompt_override 参数
2. 意图识别增加缓存（相同输入短时间内复用结果）
3. 增加更多意图的模板化快速路径，减少不必要的 LLM DAG 规划调用
"""

from typing import Any, Dict, List, Optional
from loguru import logger
import json
import re
import hashlib
import time

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


# 意图代码 → 中文标签映射
INTENT_LABELS: Dict[str, str] = {
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
    "COMPLEX_TASK": "复合任务",
}

# 意图分类 Prompt
INTENT_CLASSIFICATION_PROMPT = """你是一个专业的法务意图识别专家。请分析用户的输入，判断其最符合的意图类型。

可选的意图类型：
1. **QA_CONSULTATION**: 简单的法律问答、咨询、概念解释。不需要复杂的多步骤处理。
   - 示例："违反劳动法怎么赔偿？", "什么是不可抗力？"
2. **CONTRACT_REVIEW**: 需要审查合同、协议、条款。
   - 示例："帮我看看这个合同有没有坑", "审查附件中的租房协议"
3. **DUE_DILIGENCE**: 需要调查公司背景、风险、信用。
   - 示例："查一下腾讯公司的背景", "这家公司有诉讼记录吗"
4. **DOCUMENT_DRAFTING**: 需要起草、撰写法律文书。
   - 示例："帮我写一份离婚协议书", "起草律师函"
5. **COMPLEX_TASK**: 复杂的、混合的、不确定的任务，需要多步规划。
   - 示例："我想起诉这家公司，帮我评估风险并准备材料，还要查一下他们的资产"
6. **LITIGATION_STRATEGY**: 需要制定诉讼策略、分析胜诉率。
   - 示例："这案子胜算多大", "我想起诉，有什么策略", "对方反诉了怎么办"
7. **IP_PROTECTION**: 知识产权相关的查询、侵权分析。
   - 示例："对方侵犯了我的专利", "申请商标需要什么", "这个设计算侵权吗"
8. **REGULATORY_MONITORING**: 政策法规监测与解读。
   - 示例："最近有什么关于数据出境的新规", "解读一下最新的反垄断法"
9. **TAX_FINANCE**: 财税、发票、财务合规相关。
   - 示例："这笔报销合规吗", "怎么做研发费用加计扣除", "股权转让怎么避税"
10. **LABOR_HR**: 劳动人事、员工管理相关。
   - 示例："辞退员工要赔多少钱", "帮我审一下员工手册", "试用期不合格怎么处理"
11. **EVIDENCE_PROCESSING**: 涉及具体的证据材料处理（图片、音频等）或证据链分析。
   - 示例："帮我分析这段录音", "把这个合同扫描件转成文字并分析", "这些证据能证明他违约吗"
12. **E_SIGNATURE**: 电子签约相关请求。
   - 示例："把这个合同发给张三签字", "发起签约", "我要签这个文件"
13. **CONTRACT_MANAGEMENT**: 合同归档、查询状态、履约提醒。
   - 示例："把这个合同归档", "提醒我什么时候收钱", "这个合同快到期了吗"
14. **POLICY_DISTRIBUTION**: 规章制度、公告的发布与全员签收。
   - 示例："发布新的考勤制度", "通知全员签署员工手册", "发个放假公告", "查看谁还没签收"

输出格式 (严格JSON):
{
  "intent": "QA_CONSULTATION" | "CONTRACT_REVIEW" | "DUE_DILIGENCE" | "DOCUMENT_DRAFTING" | "LITIGATION_STRATEGY" | "IP_PROTECTION" | "REGULATORY_MONITORING" | "TAX_FINANCE" | "LABOR_HR" | "EVIDENCE_PROCESSING" | "E_SIGNATURE" | "CONTRACT_MANAGEMENT" | "POLICY_DISTRIBUTION" | "COMPLEX_TASK",
  "confidence": 0.95,
  "reasoning": "用户..."
}
"""

# 核心规划 Prompt (支持历史经验)
COORDINATOR_PROMPT_V2 = """你是AI法务系统的核心协调调度专家。

### 你的任务
基于用户需求和（可选的）历史类似案件经验，制定高效的执行计划 (DAG)。

### 可用的专业智能体
- `legal_advisor`: 法律顾问 (通用咨询, 案件初步分析)
- `contract_reviewer`: 合同审查专家 (风险识别, 条款审核)
- `due_diligence`: 尽调专家 (企业背景, 信用检索)
- `legal_researcher`: 法规研究员 (查法条, 找案例)
- `document_drafter`: 文书专家 (起草文书)
- `compliance_officer`: 合规官 (合规检查)
- `risk_assessor`: 风险评估专家 (综合评分)
- `litigation_strategist`: 诉讼策略专家 (制定诉讼方案, 庭审准备)
- `ip_specialist`: 知识产权专家 (IP侵权分析, 维权)
- `regulatory_monitor`: 监管合规监测 (政策解读, 合规预警)
- `tax_compliance`: 财税合规专家 (税务合规, 财务风险)
- `labor_compliance`: 劳动人事专家 (员工关系, 规章制度)
- `evidence_analyst`: 证据分析专家 (OCR/ASR多模态处理, 证据链分析)
- `contract_steward`: 合同管家 (归档, 履约监控, 智能提醒)

### 历史经验参考
{similar_cases_context}

### 输出格式 (严格JSON)
{{
  "analysis": "任务深度解析...",
  "plan": [
    {{
      "id": "task_1",
      "agent": "agent_name",
      "instruction": "具体指令...",
      "depends_on": [] 
    }}
  ],
  "reasoning": "规划理由...",
  "priority": "normal"
}}

注意：
1. 如果有历史经验，**优先参考**历史经验中的有效路径。
2. 保持计划尽可能并行化。
"""

# ========== 意图到 Agent 的模板化快速路径映射 ==========
# 这些意图可以不经过 LLM DAG 规划，直接生成固定计划
FAST_PATH_ROUTES: Dict[str, List[Dict[str, Any]]] = {
    "QA_CONSULTATION": [
        {"id": "task_1", "agent": "legal_advisor", "depends_on": []}
    ],
    "CONTRACT_REVIEW": [
        {"id": "task_1", "agent": "contract_reviewer", "depends_on": []},
        {"id": "task_2", "agent": "risk_assessor", "instruction_suffix": "基于合同审查结果，评估综合风险。", "depends_on": ["task_1"]},
    ],
    "DUE_DILIGENCE": [
        {"id": "task_1", "agent": "due_diligence", "depends_on": []},
    ],
    "DOCUMENT_DRAFTING": [
        {"id": "task_1", "agent": "document_drafter", "depends_on": []},
    ],
    "LITIGATION_STRATEGY": [
        {"id": "task_1", "agent": "legal_researcher", "instruction_suffix": "查找相关法条和案例。", "depends_on": []},
        {"id": "task_2", "agent": "litigation_strategist", "instruction_suffix": "制定诉讼策略。", "depends_on": ["task_1"]},
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
    _intent_cache: Dict[str, tuple] = {}
    INTENT_CACHE_TTL = 300  # 5分钟
    
    def __init__(self):
        config = AgentConfig(
            name="协调调度Agent",
            role="协调者",
            description="意图识别、任务编排、结果汇总",
            system_prompt="你是AI法务系统的核心大脑。",
            temperature=0.1,
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理任务入口"""
        analysis_result = await self.analyze_task(task)
        
        return AgentResponse(
            agent_name=self.name,
            content=analysis_result.get("analysis", "任务规划完成"),
            metadata=analysis_result
        )
    
    async def analyze_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
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
                res = await multimodal_service.process_file(f_path, f_path.split('/')[-1])
                processed_files.append(res)
                description += f"\n\n[附件上下文] 文件名: {res['file_name']}, 类型: {res['file_type']}, 摘要: {res.get('summary', '')}"
            context["processed_files"] = processed_files

        logger.info(f"Coordinator 开始分析任务: {description[:50]}...")
        if intent_hint:
            logger.info(f"  辅助意图提示: {intent_hint}")
        
        # --- Stage 1: 意图识别（极速路径优先 → 缓存 → LLM 兜底）---
        # 1a) 关键词规则引擎：0ms 级别匹配，覆盖 80% 常见场景
        intent_data = self._fast_keyword_intent(description)
        if intent_data and intent_data.get("confidence", 0) >= 0.8:
            intent = intent_data["intent"]
            confidence = intent_data["confidence"]
            logger.info(f"⚡ 极速意图(关键词): {intent} (置信度: {confidence})")
        else:
            # 1b) LLM 意图分类（带缓存，仅复杂/模糊消息）
            intent_data = await self._classify_intent(description)
            intent = intent_data.get("intent", "COMPLEX_TASK")
            confidence = intent_data.get("confidence", 0.0)
            logger.info(f"意图识别结果(LLM): {intent} (置信度: {confidence})")

        hint_mapping = {
            "find_lawyer": "QA_CONSULTATION",
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
    
    def _decide_response_strategy(self, intent: str, description: str, context: Dict[str, Any]) -> str:
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
        _clarity_keywords_strong = ['审查', '起草', '尽职调查', '风险评估', '诉讼策略', '签约', '归档']
        _clarity_keywords_partial = ['合同', '律师', '纠纷', '赔偿', '员工', '税务', '专利']
        
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
            if intent in {"DOCUMENT_DRAFTING", "E_SIGNATURE", "EVIDENCE_PROCESSING",
                          "CONTRACT_REVIEW", "CONTRACT_MANAGEMENT"}:
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
        if intent in {"DUE_DILIGENCE", "LITIGATION_STRATEGY", "IP_PROTECTION",
                       "REGULATORY_MONITORING", "TAX_FINANCE", "LABOR_HR",
                       "POLICY_DISTRIBUTION"}:
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
    
    def get_scene_a2ui_config(self, intent: str) -> Dict[str, Any]:
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
                "suggested_cards": ["risk-assessment", "risk-indicator", "detail-list", "case-progress"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "risk-assessment",
                "description": "尽职调查结果以风险雷达图+风险仪表盘+详情列表展示，流式逐步推送",
            },
            "LITIGATION_STRATEGY": {
                "suggested_cards": ["risk-assessment", "case-progress", "fee-estimate", "recommendation-card"],
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
                "suggested_cards": ["risk-assessment", "detail-list", "info-banner"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "risk-assessment",
                "description": "合规监管以风险评估雷达+详情+警示横幅展示",
            },
            "COMPLEX_TASK": {
                "suggested_cards": ["case-progress", "risk-assessment", "detail-list"],
                "layout": "vertical",
                "streaming_hint": True,
                "primary_card": "case-progress",
                "description": "复杂任务以案件进度+风险评估+详情展示，流式推送",
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
        return scene_map.get(intent, {
            "suggested_cards": [],
            "layout": "vertical",
            "streaming_hint": False,
            "primary_card": None,
            "description": "默认纯文本展示",
        })

    # ========== 极速关键词意图匹配（0ms 级别，跳过 LLM）==========
    
    # 关键词 → 意图映射表（按优先级排列，越靠前越优先）
    # 注意：关键词仅匹配用户输入的前 200 字符（即用户实际问题），避免合同正文干扰
    _KEYWORD_INTENT_RULES = [
        # (关键词列表, 意图, 置信度)
        (["审查合同", "合同审查", "审合同", "审查这份", "审查一下", "条款审核", "合同风险", "帮我审查"], "CONTRACT_REVIEW", 0.92),
        (["电子签", "发起签约", "电子签章", "电子签约", "在线签署"], "E_SIGNATURE", 0.92),
        (["归档", "合同到期", "履约提醒", "合同管理", "合同状态"], "CONTRACT_MANAGEMENT", 0.90),
        (["发布制度", "签收", "全员通知", "公告", "员工手册发布"], "POLICY_DISTRIBUTION", 0.90),
        (["起草", "草拟", "写一份", "拟一份", "律师函", "法律文书", "法律意见书"], "DOCUMENT_DRAFTING", 0.90),
        (["尽职调查", "尽调", "背景调查", "企业调查", "查公司", "调查公司", "查一下公司", "看看公司", "公司怎么样", "工商信息", "股权结构", "诉讼记录", "信用记录", "供应商靠不靠谱", "合作方风险", "交易对手背景"], "DUE_DILIGENCE", 0.90),
        (["诉讼策略", "起诉", "胜诉", "败诉", "庭审", "反诉", "仲裁"], "LITIGATION_STRATEGY", 0.88),
        (["风险评估", "合规检查", "合规审查", "合规风险"], "REGULATORY_MONITORING", 0.88),
        (["专利", "商标", "侵权", "知识产权", "版权"], "IP_PROTECTION", 0.88),
        (["辞退", "劳动合同", "劳动仲裁", "工资拖欠", "员工", "入职", "试用期", "社保", "劳动争议", "劳动法", "工伤"], "LABOR_HR", 0.88),
        (["发票", "报销", "税务", "财税", "避税", "税收", "股权转让"], "TAX_FINANCE", 0.88),
        (["录音", "证据", "鉴定", "证据链"], "EVIDENCE_PROCESSING", 0.88),
        (["新规", "政策", "法规解读", "监管"], "REGULATORY_MONITORING", 0.85),
    ]
    
    def _fast_keyword_intent(self, description: str) -> Optional[Dict[str, Any]]:
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

    async def _classify_intent(self, description: str) -> Dict[str, Any]:
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
                system_prompt_override=INTENT_CLASSIFICATION_PROMPT,
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

    def _cleanup_intent_cache(self):
        """清理过期的意图缓存条目"""
        now = time.time()
        expired_keys = [
            k for k, (_, t) in self._intent_cache.items()
            if now - t > self.INTENT_CACHE_TTL
        ]
        for k in expired_keys:
            del self._intent_cache[k]

    def _generate_template_plan(self, description: str, intent: str) -> Dict[str, Any]:
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
        context: Dict[str, Any], 
        similar_cases: List[Dict[str, Any]],
        intent: str
    ) -> Dict[str, Any]:
        """生成 DAG 计划（仅用于 COMPLEX_TASK）"""
        
        # 构建历史经验上下文文本
        similar_cases_text = "无相关历史经验"
        if similar_cases:
            cases_str = []
            for i, case in enumerate(similar_cases[:2]):
                cases_str.append(
                    f"案例 {i+1}:\n- 任务: {case.get('task')}\n"
                    f"- 之前的计划: {json.dumps(case.get('plan'), ensure_ascii=False)}"
                )
            similar_cases_text = "\n\n".join(cases_str)
            logger.info("已注入历史经验上下文用于规划")

        final_prompt_sys = COORDINATOR_PROMPT_V2.format(similar_cases_context=similar_cases_text)
        user_prompt = f"需求描述：{description}\n识别意图：{intent}\n上下文信息：{str(context)[:500]}"
        
        try:
            # 使用 system_prompt_override 而不是修改实例状态 + 重建客户端
            response_text = await self.chat(
                user_prompt,
                system_prompt_override=final_prompt_sys
            )
            
            plan_data = self._parse_json(response_text)
            plan_data["intent"] = intent
            return plan_data
            
        except Exception as e:
            logger.error(f"DAG 规划失败: {e}")
            return await self._fallback_analysis(description)

    async def _fallback_analysis(self, description: str) -> Dict[str, Any]:
        """兜底规划（规则引擎）"""
        agents = ["legal_advisor"]
        
        if "合同" in description: agents = ["contract_reviewer"]
        elif "尽调" in description: agents = ["due_diligence"]
        elif "诉讼" in description or "仲裁" in description: agents = ["litigation_strategist"]
        elif "知识产权" in description or "专利" in description or "商标" in description or "侵权" in description: agents = ["ip_specialist"]
        elif "监管" in description or "新规" in description or "政策" in description: agents = ["regulatory_monitor"]
        elif "税" in description or "财务" in description or "发票" in description: agents = ["tax_compliance"]
        elif "员工" in description or "辞退" in description or "劳动" in description or "入职" in description: agents = ["labor_compliance"]
        elif "证据" in description or "录音" in description or "扫描" in description or "图片" in description: agents = ["evidence_analyst"]
        elif "签约" in description or "签字" in description or "盖章" in description: agents = ["contract_steward"]
        elif "归档" in description or "提醒" in description or "到期" in description: agents = ["contract_steward"]
        elif "制度" in description or "公告" in description or "手册" in description or "通知" in description: agents = ["labor_compliance"]
        
        plan = [{
            "id": "task_1",
            "agent": agents[0],
            "instruction": description,
            "depends_on": []
        }]
        
        return {
            "analysis": "规则引擎兜底规划",
            "plan": plan,
            "intent": "UNKNOWN",
            "reasoning": "Fallback",
            "total_steps": 1
        }

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """辅助 JSON 解析"""
        if not text:
            return {}
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except (json.JSONDecodeError, TypeError):
                    pass
        return {}

    async def aggregate_results(self, results: List[AgentResponse]) -> Dict[str, Any]:
        """汇总结果"""
        from datetime import datetime
        
        summary = "任务执行完成。\n\n"
        for r in results:
            if isinstance(r, AgentResponse):
                summary += f"### {r.agent_name}\n{r.content}\n\n"
                
        return {
            "summary": summary,
            "agent_count": len(results),
            "generated_at": datetime.now().isoformat()
        }

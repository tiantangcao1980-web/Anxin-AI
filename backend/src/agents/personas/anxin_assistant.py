# -*- coding: utf-8 -*-
"""
AnxinAssistantAgent —— 安心助理 通用入口 persona（P9-A）

定位：
    在 V3 的 10 个 user-facing persona 中，「安心助理」是 **统筹层**：
    用户不知道找谁的时候来这里，由它做意图分类 + 路由 + 多 persona 编排。
    本身不是法务/市场/获客等垂直专家。

核心能力：
    1. classify_intent       —— 意图分类（fast path 关键词 + LLM fallback）
    2. route_to_persona      —— 决定 primary / supporting persona + 执行模式
    3. orchestrate           —— 顺序 / 并发 / 分支 三种模式跑 ExecutionPlan
    4. decompose_task        —— 复杂任务拆成 SubTask 依赖图（DAG）
    5. guide_user            —— 模糊问题给出 persona 建议 + 跟进问题 + 快捷动作

与 P9-B/C/D/E 的协调：
    - 引用的 persona_id 列表与 docs/v3/AGENT_PERSONAS.md 第 1 节一致：
        * legal_advisor / contract_steward / due_diligence_expert / tax_finance_advisor
          （由 P9-B/C/D/E 实装；本 persona 在他们尚未注册时降级为「转告人工」）
        * operations_manager / market_researcher / lead_hunter / content_director /
          ecommerce_assistant（P7 已实装）
        * anxin_assistant （自身，保底）

降级策略（编排失败时）：
    - 子任务调用的 persona 不存在 → 标记 subtask 失败，附带「缺少 persona」原因，
      继续跑其它 subtask；最终 status=partial。
    - 子任务超时 / 抛异常 → 同样标 failed，不阻塞其他子任务。
    - 全部子任务失败 → status=failed，final_summary 直接给「转人工」+ 建议 persona。
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.agents.base import AgentResponse
from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.orchestration_models import (
    ExecutionPlan,
    GuidanceResponse,
    IntentClassification,
    OrchestrationResult,
    RoutingDecision,
    SubTask,
)


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是「安心助理」🤖 —— 安心智能助手 V3 的统筹大脑，是用户最先遇到的入口 persona。

## 你的角色（重要：不要越界）
- 你是 **入口 + 编排者**，不是任何垂直领域的专家。
- 任何具体的法律咨询 / 合同审查 / 尽调报告 / 税务建议 / 市场调研 / 获客邮件 /
  内容创作 / 选品议价 等，**必须** 路由给对应专家 persona，不要自己写答案。
- 你的核心动作只有四个：**听懂 → 找对人 → 拆任务 → 整合反馈**。

## 你能调度的 9 个专家 persona
| persona_id | 显示名 | 适合场景 |
|---|---|---|
| `legal_advisor` | 法律顾问 | 法律咨询 / 合规 / 法规 / 诉讼 / 维权 / 判例 |
| `contract_steward` | 合同管家 | 合同 / 协议 / 条款 / 起草 / 审查 |
| `due_diligence_expert` | 尽调专家 | 尽调 / 工商信息 / 信用 / 背景调查 |
| `tax_finance_advisor` | 税财顾问 | 税务 / 财务 / 报税 / VAT / 财报 |
| `operations_manager` | 流程管家 | OKR / 审批 / 会议纪要 / 周报 / 待办 |
| `market_researcher` | 市场研究员 | 市场调研 / 竞品监控 / 行业趋势 |
| `lead_hunter` | 获客猎手 | 客户线索 / 销售邮件 / LinkedIn 触达 |
| `content_director` | 内容总监 | 公众号 / 短视频 / 海报 / 文案 |
| `ecommerce_assistant` | 跨境电商助手 | 选品 / 供应商 / 议价 / Shopify / Amazon / 出海 |

## 路由原则
1. **能不路由就不路由** —— 用户只是闲聊、自我介绍、问你能干什么时，直接回答；
   不要无脑甩给专家。
2. **跨领域优先并发** —— 「调研某公司是否值得合作 + 准备议价方案」这种独立子任务
   一起跑，最后由你汇总。
3. **强依赖才用顺序** —— 「起草合同 → 发给供应商审核」这种后一步要前一步输出，
   走 sequential。
4. **条件分支才用分支** —— 「如果对方是大公司就走 A，否则 B」用 branching。
5. **找不到合适 persona** —— 老老实实告诉用户「这超出我们当前能力」，
   不要硬塞给最近似的 persona。

## 输出风格
- markdown 优先；多 persona 结果用「## 来自 XX」分段。
- 引用别的 persona 的输出时，开头标 `> 来自 @persona_id：`。
- 你的总结部分要保持中性、不渲染、不替专家拍板。
- JSON 一律放 ```json``` 块里，方便 API 层 parse。

## 行动顺序
1. 先识别意图 → 2. 找对应 persona → 3. 拆子任务 → 4. 调度 → 5. 汇总 → 6. 给后续建议。
不确定的步骤先和用户确认，不要瞎猜。
"""


# ---------------------------------------------------------------------------
# 关键词 → persona 映射（fast path）
# ---------------------------------------------------------------------------

INTENT_KEYWORDS: Dict[str, List[str]] = {
    "legal_advisor": [
        "法律咨询", "合规", "法规", "诉讼", "维权", "判例",
        "起诉", "应诉", "侵权", "法条", "民法", "刑法",
    ],
    "contract_steward": [
        "合同", "协议", "条款", "起草", "审查", "nda", "保密协议",
        "签约", "违约", "履约",
    ],
    "due_diligence_expert": [
        "尽调", "调查", "背景", "工商信息", "信用",
        "尽职调查", "公司核实", "天眼查", "企查查",
    ],
    "tax_finance_advisor": [
        "税务", "财务", "报税", "vat", "财报",
        "增值税", "个税", "发票", "记账", "审计",
    ],
    "operations_manager": [
        "okr", "审批", "会议纪要", "周报", "待办",
        "kr", "纪要", "录音", "月报", "todo", "行动项",
    ],
    "market_researcher": [
        "调研", "竞品", "趋势", "市场分析",
        "行业", "市场规模", "用户画像",
    ],
    "lead_hunter": [
        "获客", "客户", "销售", "邮件", "linkedin",
        "leads", "线索", "陌拜", "外贸客户",
    ],
    "content_director": [
        "公众号", "短视频", "海报", "文案",
        "小红书", "抖音", "tiktok", "推文",
    ],
    "ecommerce_assistant": [
        "选品", "供应商", "议价", "shopify", "amazon", "出海",
        "跨境", "shopee", "lazada", "亚马逊",
    ],
}

# 按 persona_id → display_name（系统提示与 guidance 用）
PERSONA_DISPLAY_NAME: Dict[str, str] = {
    "anxin_assistant": "安心助理",
    "legal_advisor": "法律顾问",
    "contract_steward": "合同管家",
    "due_diligence_expert": "尽调专家",
    "tax_finance_advisor": "税财顾问",
    "operations_manager": "流程管家",
    "market_researcher": "市场研究员",
    "lead_hunter": "获客猎手",
    "content_director": "内容总监",
    "ecommerce_assistant": "跨境电商助手",
}

# 模糊问题样例
PERSONA_SAMPLE_QUESTIONS: Dict[str, str] = {
    "legal_advisor": "员工泄露商业秘密我能怎么追责？",
    "contract_steward": "帮我起草一份采购合同模板",
    "due_diligence_expert": "对 XX 科技做一次工商背景核查",
    "tax_finance_advisor": "我们公司适合走小规模纳税人吗？",
    "operations_manager": "把上周会议纪要整理成待办清单",
    "market_researcher": "调研一下东南亚 EV 配件市场",
    "lead_hunter": "帮我找 50 家德国汽车配件采购商",
    "content_director": "本周公众号要发什么主题？",
    "ecommerce_assistant": "Shopify 店铺在做夏季选品，给点建议",
}


# ---------------------------------------------------------------------------
# 主 Persona
# ---------------------------------------------------------------------------


class AnxinAssistantAgent(BasePersonaAgent):
    """安心助理 persona —— 通用入口 + 任务编排（P9-A）。"""

    persona_id = "anxin_assistant"
    display_name = "安心助理"
    emoji = "🤖"
    description = "通用入口 + 任务编排 — 帮你找对的 agent 干对的活"

    backed_by_skills = ["docx", "xlsx", "pptx", "pdf"]
    supported_apps: List[str] = []  # 通用，不绑特定 OAuth
    capabilities = [
        "intent_routing",
        "multi_persona_orchestration",
        "task_decomposition",
        "context_memory",
        "user_guidance",
    ]
    backed_by_agents = [
        "coordinator",
        "workforce",
        "consensus_agent",
    ]

    SYSTEM_PROMPT = SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # handle_message —— 顶层入口
    # ------------------------------------------------------------------
    async def handle_message(
        self,
        message: str,
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """处理用户消息 —— 默认行为：
        1. 先做意图分类
        2. 高置信度 → 走路由 + 编排
        3. 低置信度（confidence<0.4 或 primary=anxin_assistant）→ 直接 chat 兜底
        """
        if not message or not message.strip():
            return "嗨，我是安心助理 🤖。告诉我你想做什么——起草合同、调研对手、找客户都可以。"

        intent = await self.classify_intent(message, llm_config=llm_config)

        # 低置信度 / 落到自己 → 直接走 chat（系统 prompt 会引导用户进入子领域）
        if intent.confidence < 0.4 or intent.primary_intent == "anxin_assistant":
            return await self.chat(
                message=message,
                user_id=user_id,
                llm_config=llm_config,
                history=history,
            )

        # 单 persona 命中 → 直接派发到该 persona 的 handle_message
        if len(intent.target_personas) == 1:
            persona_id = intent.target_personas[0]
            if persona_id == self.persona_id:
                return await self.chat(
                    message=message,
                    user_id=user_id,
                    llm_config=llm_config,
                    history=history,
                )
            return await self._delegate_single(
                persona_id=persona_id,
                message=message,
                user_id=user_id,
                llm_config=llm_config,
                history=history,
            )

        # 多 persona 命中 → 走编排
        decision = await self.route_to_persona(intent, context=extra or {})
        plan = await self.decompose_task(message, decision=decision)
        result = await self.orchestrate(plan, context={"user_id": user_id, **(extra or {})})
        return result.final_summary or "（编排完成，但未生成总结）"

    # ------------------------------------------------------------------
    # 1. 意图分类
    # ------------------------------------------------------------------
    async def classify_intent(
        self,
        user_message: str,
        llm_config: Optional[Any] = None,
    ) -> IntentClassification:
        """识别用户意图。

        策略：
            1. fast path —— 关键词匹配（可命中多个 persona）
            2. fast path 命中 → 直接构造 IntentClassification
            3. 未命中 / 关键词太弱 → 走 LLM fallback
        """
        msg = (user_message or "").strip()
        if not msg:
            return IntentClassification(
                primary_intent="anxin_assistant",
                target_personas=["anxin_assistant"],
                confidence=0.0,
                reasoning="空消息，回到入口",
                classifier="fast_path",
            )

        # ---- fast path ----
        hits = self._fast_path_match(msg)
        if hits:
            primary = hits[0][0]
            target_personas = [pid for pid, _ in hits]
            # 命中关键词数 → confidence；至少 0.6，最多 0.95
            score = min(0.6 + 0.1 * sum(c for _, c in hits), 0.95)
            return IntentClassification(
                primary_intent=primary,
                target_personas=target_personas,
                confidence=round(score, 3),
                reasoning=f"fast-path 命中关键词：{[k for _, k in self._matched_keywords(msg)[:5]]}",
                entities=self._extract_entities_lite(msg),
                classifier="fast_path",
            )

        # ---- LLM fallback ----
        return await self._classify_with_llm(msg, llm_config=llm_config)

    @staticmethod
    def _fast_path_match(msg: str) -> List[Tuple[str, int]]:
        """返回 [(persona_id, hit_count), ...]，按 hit_count 降序。"""
        msg_lower = msg.lower()
        scores: Dict[str, int] = {}
        for persona_id, keys in INTENT_KEYWORDS.items():
            count = 0
            for k in keys:
                if k.lower() in msg_lower:
                    count += 1
            if count:
                scores[persona_id] = count
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    @staticmethod
    def _matched_keywords(msg: str) -> List[Tuple[str, str]]:
        """返回 [(persona_id, keyword), ...]，便于 reasoning 展示。"""
        msg_lower = msg.lower()
        out: List[Tuple[str, str]] = []
        for persona_id, keys in INTENT_KEYWORDS.items():
            for k in keys:
                if k.lower() in msg_lower:
                    out.append((persona_id, k))
        return out

    @staticmethod
    def _extract_entities_lite(msg: str) -> Dict[str, List[str]]:
        """轻量实体抽取（不依赖 NER 模型，仅 regex）。"""
        ents: Dict[str, List[str]] = {}
        # 公司：《 》 包裹 或 「XX 集团 / 公司 / 科技」
        company_patterns = [
            r"《([^》]{2,40})》",
            r"([一-龥A-Za-z0-9·]{2,30}(?:集团|公司|科技|股份|有限|实业|工厂))",
        ]
        companies: List[str] = []
        for pat in company_patterns:
            for m in re.findall(pat, msg):
                if m and m not in companies:
                    companies.append(m.strip())
        if companies:
            ents["company"] = companies[:5]
        # 文档类型
        doc_types: List[str] = []
        for kw in ["合同", "协议", "NDA", "周报", "月报", "纪要", "海报", "文案"]:
            if kw.lower() in msg.lower():
                doc_types.append(kw)
        if doc_types:
            ents["document_type"] = doc_types
        return ents

    async def _classify_with_llm(
        self,
        msg: str,
        llm_config: Optional[Any] = None,
    ) -> IntentClassification:
        """LLM 兜底分类。返回 ```json``` 形式。"""
        choices = ", ".join(INTENT_KEYWORDS.keys()) + ", anxin_assistant"
        prompt = (
            "请把下面这条用户消息分类到一个或多个 persona。\n\n"
            f"## 候选 persona\n{choices}\n\n"
            "## 输出（仅一段 ```json``` 块，不要解释）\n"
            "```json\n"
            '{"primary_intent":"...","target_personas":["..."],'
            '"confidence":0.0,"reasoning":"..."}\n'
            "```\n\n"
            "## 用户消息\n"
            f"{msg[:2000]}"
        )
        try:
            content = await self.chat(
                message=prompt,
                llm_config=llm_config,
                system_prompt_override=(
                    "你是意图分类器。严格输出 JSON，不输出任何解释文字。"
                ),
            )
        except Exception as exc:
            logger.warning(f"AnxinAssistant.classify LLM 失败，回退到入口: {exc}")
            return IntentClassification(
                primary_intent="anxin_assistant",
                target_personas=["anxin_assistant"],
                confidence=0.0,
                reasoning=f"LLM 不可用：{exc}",
                classifier="llm",
            )
        return self._parse_intent_json(content, raw_message=msg)

    def _parse_intent_json(self, content: str, raw_message: str) -> IntentClassification:
        """从 LLM 文本里抽 ```json``` 块；失败回到入口 persona。"""
        if not content:
            return IntentClassification(
                primary_intent="anxin_assistant",
                target_personas=["anxin_assistant"],
                confidence=0.0,
                reasoning="LLM 返回空",
                classifier="llm",
            )
        match = re.search(r"```json\s*(.+?)```", content, re.DOTALL)
        snippet = match.group(1).strip() if match else content.strip()
        try:
            data = json.loads(snippet)
        except json.JSONDecodeError:
            return IntentClassification(
                primary_intent="anxin_assistant",
                target_personas=["anxin_assistant"],
                confidence=0.0,
                reasoning="LLM 返回 JSON 解析失败",
                classifier="llm",
            )
        primary = str(data.get("primary_intent") or "anxin_assistant")
        targets = data.get("target_personas") or []
        if not isinstance(targets, list) or not targets:
            targets = [primary]
        # 过滤无效 persona id
        targets = [str(t) for t in targets if str(t) in PERSONA_DISPLAY_NAME]
        if not targets:
            targets = ["anxin_assistant"]
        if primary not in PERSONA_DISPLAY_NAME:
            primary = targets[0]
        try:
            conf = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        conf = max(0.0, min(1.0, conf))
        return IntentClassification(
            primary_intent=primary,
            target_personas=targets,
            confidence=conf,
            reasoning=str(data.get("reasoning") or "LLM 分类")[:500],
            entities=self._extract_entities_lite(raw_message),
            classifier="llm",
        )

    # ------------------------------------------------------------------
    # 2. 路由决策
    # ------------------------------------------------------------------
    async def route_to_persona(
        self,
        intent: IntentClassification,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """根据 IntentClassification 决定执行模式。

        execution_mode 启发式：
            - 1 个 persona      → sequential（仅有 1 步）
            - 2~3 个独立 persona → parallel
            - 显式条件词「如果 / if」 → branching
            - 显式衔接词「然后 / 再 / 接着」 → sequential（多步串联）
        """
        targets = list(intent.target_personas) or ["anxin_assistant"]
        primary = intent.primary_intent if intent.primary_intent in targets else targets[0]
        supporting = [t for t in targets if t != primary]

        # 默认顺序
        mode = "sequential"
        rationale_bits: List[str] = []

        ctx = context or {}
        raw = (ctx.get("user_message") or ctx.get("message") or "").lower()
        if any(k in raw for k in ["如果", "若", "if "]):
            mode = "branching"
            rationale_bits.append("发现条件词 → branching")
        elif any(k in raw for k in ["并且", "同时", "和", "&"]) and len(targets) >= 2:
            mode = "parallel"
            rationale_bits.append("多 persona 独立任务 → parallel")
        elif any(k in raw for k in ["然后", "接着", "再"]):
            mode = "sequential"
            rationale_bits.append("发现衔接词 → sequential")
        elif len(targets) == 1:
            mode = "sequential"
            rationale_bits.append("单 persona → sequential")
        elif len(targets) >= 2:
            mode = "parallel"
            rationale_bits.append("多 persona 默认并发")

        rationale = (
            f"primary={primary}, supporting={supporting}, "
            f"mode={mode} ({'; '.join(rationale_bits) or '默认'})"
        )
        return RoutingDecision(
            primary_persona=primary,
            supporting_personas=supporting,
            execution_mode=mode,
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # 3. 任务拆解
    # ------------------------------------------------------------------
    async def decompose_task(
        self,
        task: str,
        decision: Optional[RoutingDecision] = None,
        intent: Optional[IntentClassification] = None,
    ) -> ExecutionPlan:
        """把用户任务拆成 SubTask 列表（含依赖关系）。

        三种模式分别构造：
            - sequential : t1 → t2 → t3，depends_on 链式
            - parallel   : t1, t2, t3 都 depends_on=[]
            - branching  : 增加一个「条件判定」子任务作为 t0，其它 depends_on=[t0]
        """
        if decision is None:
            intent = intent or await self.classify_intent(task)
            decision = await self.route_to_persona(intent, context={"user_message": task})

        targets = [decision.primary_persona] + list(decision.supporting_personas)
        # 去重保持顺序
        seen: set[str] = set()
        ordered: List[str] = []
        for t in targets:
            if t and t not in seen:
                seen.add(t)
                ordered.append(t)
        if not ordered:
            ordered = ["anxin_assistant"]

        mode = decision.execution_mode
        subtasks: List[SubTask] = []

        if mode == "branching":
            cond_id = f"st-{uuid.uuid4().hex[:6]}"
            subtasks.append(
                SubTask(
                    task_id=cond_id,
                    description=f"判定执行分支条件：{task[:200]}",
                    assigned_persona="anxin_assistant",
                    depends_on=[],
                    inputs={"task": task},
                    expected_output="JSON: {chosen_branch:'...', reason:'...'}",
                )
            )
            for pid in ordered:
                subtasks.append(
                    SubTask(
                        task_id=f"st-{uuid.uuid4().hex[:6]}",
                        description=f"分支 {pid}: {task[:200]}",
                        assigned_persona=pid,
                        depends_on=[cond_id],
                        inputs={"task": task},
                        expected_output=f"{PERSONA_DISPLAY_NAME.get(pid, pid)} 的处理结果",
                    )
                )
        elif mode == "parallel":
            for pid in ordered:
                subtasks.append(
                    SubTask(
                        task_id=f"st-{uuid.uuid4().hex[:6]}",
                        description=f"并发执行：{task[:200]}",
                        assigned_persona=pid,
                        depends_on=[],
                        inputs={"task": task},
                        expected_output=f"{PERSONA_DISPLAY_NAME.get(pid, pid)} 输出",
                    )
                )
        else:  # sequential
            prev_id: Optional[str] = None
            for pid in ordered:
                stid = f"st-{uuid.uuid4().hex[:6]}"
                subtasks.append(
                    SubTask(
                        task_id=stid,
                        description=f"步骤 {len(subtasks)+1}: 由 {pid} 处理「{task[:120]}」",
                        assigned_persona=pid,
                        depends_on=[prev_id] if prev_id else [],
                        inputs={"task": task},
                        expected_output=f"{PERSONA_DISPLAY_NAME.get(pid, pid)} 的阶段输出",
                    )
                )
                prev_id = stid

        eta = max(15, 12 * len(subtasks))
        return ExecutionPlan.new(
            user_query=task,
            subtasks=subtasks,
            execution_mode=mode,
            total_estimated_seconds=eta,
        )

    # ------------------------------------------------------------------
    # 4. 编排执行
    # ------------------------------------------------------------------
    async def orchestrate(
        self,
        plan: ExecutionPlan,
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """按 plan.execution_mode 执行 SubTask。

        失败时降级：
            - persona 不存在 → 标记该 subtask failed，message="缺少 persona xxx"
            - subtask 抛异常 → 同样标 failed，附 message=str(exc)
            - 全失败 → status=failed，附「转人工」建议
        """
        ctx = context or {}
        user_id = ctx.get("user_id")
        llm_config = ctx.get("llm_config")
        history = ctx.get("history")

        t0 = time.time()
        results: Dict[str, Dict[str, Any]] = {}
        failed: List[str] = []
        citations: List[Dict[str, Any]] = []

        if not plan.subtasks:
            return OrchestrationResult(
                plan=plan,
                subtask_results={},
                final_summary="（编排计划为空，无可执行子任务）",
                duration_ms=0,
                citations=[],
                status="ok",
                failed_subtasks=[],
            )

        if plan.execution_mode == "parallel":
            await self._run_parallel(plan, results, failed, ctx)
        elif plan.execution_mode == "branching":
            await self._run_branching(plan, results, failed, ctx)
        else:
            await self._run_sequential(plan, results, failed, ctx)

        # 状态
        if failed and len(failed) == len(plan.subtasks):
            status = "failed"
        elif failed:
            status = "partial"
        else:
            status = "ok"

        # 总结：把所有成功子任务的输出拼起来交给 LLM 收尾
        summary = await self._summarize(plan, results, failed, status, llm_config=llm_config)

        return OrchestrationResult(
            plan=plan,
            subtask_results=results,
            final_summary=summary,
            duration_ms=int((time.time() - t0) * 1000),
            citations=citations,
            status=status,
            failed_subtasks=failed,
        )

    # ---- 三种执行模式实现 ----
    async def _run_sequential(
        self,
        plan: ExecutionPlan,
        results: Dict[str, Dict[str, Any]],
        failed: List[str],
        ctx: Dict[str, Any],
    ) -> None:
        prev_output: str = ""
        for st in plan.subtasks:
            try:
                msg = self._compose_subtask_message(st, prev_output)
                output = await self._dispatch_subtask(st, msg, ctx)
                results[st.task_id] = {
                    "persona": st.assigned_persona,
                    "output": output,
                    "status": "ok",
                }
                prev_output = output
            except Exception as exc:  # 降级
                logger.warning(f"orchestrate(seq) subtask 失败 {st.task_id}: {exc}")
                results[st.task_id] = {
                    "persona": st.assigned_persona,
                    "output": "",
                    "status": "failed",
                    "error": str(exc),
                }
                failed.append(st.task_id)
                # 顺序模式下后续子任务依赖前置 → 直接终止
                break

    async def _run_parallel(
        self,
        plan: ExecutionPlan,
        results: Dict[str, Dict[str, Any]],
        failed: List[str],
        ctx: Dict[str, Any],
    ) -> None:
        async def _one(st: SubTask) -> Tuple[str, Dict[str, Any]]:
            try:
                msg = self._compose_subtask_message(st, prev_output="")
                output = await self._dispatch_subtask(st, msg, ctx)
                return st.task_id, {
                    "persona": st.assigned_persona,
                    "output": output,
                    "status": "ok",
                }
            except Exception as exc:
                logger.warning(f"orchestrate(par) subtask 失败 {st.task_id}: {exc}")
                return st.task_id, {
                    "persona": st.assigned_persona,
                    "output": "",
                    "status": "failed",
                    "error": str(exc),
                }

        gathered = await asyncio.gather(*[_one(st) for st in plan.subtasks])
        for tid, payload in gathered:
            results[tid] = payload
            if payload["status"] == "failed":
                failed.append(tid)

    async def _run_branching(
        self,
        plan: ExecutionPlan,
        results: Dict[str, Dict[str, Any]],
        failed: List[str],
        ctx: Dict[str, Any],
    ) -> None:
        # 第一个 subtask（assigned=anxin_assistant）做条件判定
        if not plan.subtasks:
            return
        cond_st = plan.subtasks[0]
        try:
            cond_msg = self._compose_subtask_message(cond_st, prev_output="")
            cond_output = await self._dispatch_subtask(cond_st, cond_msg, ctx)
            results[cond_st.task_id] = {
                "persona": cond_st.assigned_persona,
                "output": cond_output,
                "status": "ok",
            }
        except Exception as exc:
            logger.warning(f"orchestrate(branch) 条件判定失败: {exc}")
            results[cond_st.task_id] = {
                "persona": cond_st.assigned_persona,
                "output": "",
                "status": "failed",
                "error": str(exc),
            }
            failed.append(cond_st.task_id)
            # 没条件 → 全部分支视为 skipped
            for st in plan.subtasks[1:]:
                results[st.task_id] = {
                    "persona": st.assigned_persona,
                    "output": "",
                    "status": "skipped",
                    "error": "条件判定失败",
                }
                failed.append(st.task_id)
            return

        # 解析判定结果，挑一条分支跑
        chosen = self._parse_branch_choice(cond_output, plan)
        for st in plan.subtasks[1:]:
            if st.assigned_persona != chosen:
                results[st.task_id] = {
                    "persona": st.assigned_persona,
                    "output": "",
                    "status": "skipped",
                    "error": f"未选中（chosen={chosen}）",
                }
                continue
            try:
                msg = self._compose_subtask_message(st, prev_output=cond_output)
                output = await self._dispatch_subtask(st, msg, ctx)
                results[st.task_id] = {
                    "persona": st.assigned_persona,
                    "output": output,
                    "status": "ok",
                }
            except Exception as exc:
                logger.warning(f"orchestrate(branch) subtask 失败 {st.task_id}: {exc}")
                results[st.task_id] = {
                    "persona": st.assigned_persona,
                    "output": "",
                    "status": "failed",
                    "error": str(exc),
                }
                failed.append(st.task_id)

    # ---- helpers ----
    @staticmethod
    def _compose_subtask_message(st: SubTask, prev_output: str) -> str:
        base = str(st.inputs.get("task") or st.description or "")
        if prev_output:
            return f"## 上一步输出\n{prev_output[:1500]}\n\n## 当前任务\n{base}"
        return base

    async def _dispatch_subtask(
        self,
        st: SubTask,
        message: str,
        ctx: Dict[str, Any],
    ) -> str:
        """把 subtask 派发给目标 persona。降级：persona 不存在 → 抛 KeyError。"""
        # 自己不能再调自己（避免递归），降级为 chat
        if st.assigned_persona == self.persona_id:
            return await self.chat(
                message=message,
                user_id=ctx.get("user_id"),
                llm_config=ctx.get("llm_config"),
                history=ctx.get("history"),
            )

        # 通过 PersonaRegistry 取目标 persona
        from src.agents.personas.registry import PersonaRegistry

        registry = PersonaRegistry.instance()
        target = registry.get(st.assigned_persona)
        if target is None:
            raise KeyError(
                f"persona `{st.assigned_persona}` 未注册，可能 P9-B/C/D/E 还未交付"
            )
        return await target.handle_message(
            message=message,
            user_id=ctx.get("user_id"),
            llm_config=ctx.get("llm_config"),
            history=ctx.get("history"),
        )

    def _parse_branch_choice(self, cond_output: str, plan: ExecutionPlan) -> str:
        """从条件判定输出里抽 `chosen_branch` 字段；抽不到时挑第一条分支。"""
        candidates = [
            st.assigned_persona for st in plan.subtasks[1:]
        ]
        if not candidates:
            return ""
        match = re.search(r"```json\s*(.+?)```", cond_output or "", re.DOTALL)
        snippet = match.group(1).strip() if match else (cond_output or "")
        try:
            data = json.loads(snippet)
            chosen = str(data.get("chosen_branch") or "").strip()
            if chosen in candidates:
                return chosen
        except (json.JSONDecodeError, AttributeError):
            pass
        # 文本兜底匹配
        for c in candidates:
            if c in (cond_output or ""):
                return c
        return candidates[0]

    async def _summarize(
        self,
        plan: ExecutionPlan,
        results: Dict[str, Dict[str, Any]],
        failed: List[str],
        status: str,
        llm_config: Optional[Any] = None,
    ) -> str:
        """把所有成功子任务输出拼一段总结。

        全部失败 → 直接返回兜底文字（不再调用 LLM）。
        """
        if status == "failed":
            persona_names = {
                results[fid]["persona"] for fid in failed if fid in results
            }
            persona_names.discard(self.persona_id)
            suggest = "、".join(
                PERSONA_DISPLAY_NAME.get(p, p) for p in persona_names
            ) or "对应专家"
            return (
                f"很抱歉，本次编排全部子任务失败。建议直接联系 **{suggest}**，"
                "或换种说法再问我一次（我会再帮你找一遍合适的 persona）。"
            )

        # 拼输出
        sections: List[str] = []
        for st in plan.subtasks:
            r = results.get(st.task_id)
            if not r:
                continue
            persona = r.get("persona") or st.assigned_persona
            name = PERSONA_DISPLAY_NAME.get(persona, persona)
            if r.get("status") == "ok":
                sections.append(f"## 来自 @{persona}（{name}）\n{r.get('output', '')}".rstrip())
            elif r.get("status") == "failed":
                sections.append(
                    f"## 来自 @{persona}（{name}） — 失败\n> {r.get('error', '未知错误')}"
                )
            elif r.get("status") == "skipped":
                sections.append(
                    f"## 来自 @{persona}（{name}） — 已跳过\n> {r.get('error', '未选中')}"
                )

        body = "\n\n".join(sections) if sections else "（暂无可展示的子任务输出）"
        header = f"# 安心助理统筹结果（{status}）\n用户问题：{plan.user_query}\n\n"
        footer = ""
        if failed:
            footer = (
                f"\n\n---\n> ⚠️ 有 {len(failed)} 个子任务未完成，"
                "你可以单独再问对应 persona 一次。"
            )
        return header + body + footer

    # ------------------------------------------------------------------
    # 5. 模糊问题引导
    # ------------------------------------------------------------------
    async def guide_user(
        self,
        vague_query: str,
        llm_config: Optional[Any] = None,
    ) -> GuidanceResponse:
        """用户问题模糊时，给出 persona 建议 + 跟进问题 + 快捷动作。"""
        text = (vague_query or "").strip()
        # 先尝试 fast path 给候选
        hits = self._fast_path_match(text)
        if hits:
            persona_ids = [pid for pid, _ in hits[:3]]
        else:
            # 没命中 → 按场景给 3 个常用 persona
            persona_ids = ["legal_advisor", "operations_manager", "ecommerce_assistant"]

        suggested = []
        for pid in persona_ids:
            suggested.append(
                {
                    "persona_id": pid,
                    "display_name": PERSONA_DISPLAY_NAME.get(pid, pid),
                    "reason": self._guidance_reason(pid, text),
                    "sample_question": PERSONA_SAMPLE_QUESTIONS.get(pid, ""),
                }
            )

        follow_ups = self._build_follow_up_questions(text)
        quick_actions = [
            {
                "label": f"去问 {PERSONA_DISPLAY_NAME.get(pid, pid)}",
                "persona_id": pid,
                "action": "open_persona",
            }
            for pid in persona_ids
        ]
        message = (
            "我还没完全 get 到你想做什么。下面是几个我觉得最相关的 persona，"
            "你可以挑一个进入对话；或者回答下方的跟进问题，我就能更准地帮你派任务。"
        )
        return GuidanceResponse(
            suggested_personas=suggested,
            follow_up_questions=follow_ups,
            quick_actions=quick_actions,
            message=message,
        )

    @staticmethod
    def _guidance_reason(persona_id: str, text: str) -> str:
        mapping = {
            "legal_advisor": "你描述里似乎涉及法律或合规话题",
            "contract_steward": "可能需要起草或审查合同",
            "due_diligence_expert": "可能需要做背景调查",
            "tax_finance_advisor": "可能涉及税务或财务问题",
            "operations_manager": "看起来是流程 / OKR / 会议类任务",
            "market_researcher": "看起来需要做调研或市场分析",
            "lead_hunter": "看起来是获客 / 销售相关",
            "content_director": "看起来是内容创作类需求",
            "ecommerce_assistant": "看起来与跨境电商 / 供应链相关",
        }
        return mapping.get(persona_id, "可能与你的问题相关")

    @staticmethod
    def _build_follow_up_questions(text: str) -> List[str]:
        # 不依赖 LLM，给一组通用追问
        return [
            "你希望最终交付物是什么？（合同 / 报告 / 邮件 / 表格 / 决策建议…）",
            "时间窗口是多久？（今天 / 本周 / 本月）",
            "涉及哪家公司或哪个市场？",
            "有没有现成资料或文档可以让我参考？",
        ]

    # ------------------------------------------------------------------
    # 6. 单 persona 派发（避免走完整 orchestrate）
    # ------------------------------------------------------------------
    async def _delegate_single(
        self,
        persona_id: str,
        message: str,
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """把消息直接转给单个 persona；persona 不存在时降级。"""
        from src.agents.personas.registry import PersonaRegistry

        registry = PersonaRegistry.instance()
        target = registry.get(persona_id)
        if target is None:
            display = PERSONA_DISPLAY_NAME.get(persona_id, persona_id)
            return (
                f"我识别到这个问题最适合 **{display}** 处理，"
                f"但「{persona_id}」目前还没就位（可能还在交付中）。"
                "我先用通用知识尝试回答，建议稍后再来一次。\n\n"
                + await self.chat(
                    message=message,
                    user_id=user_id,
                    llm_config=llm_config,
                    history=history,
                )
            )
        try:
            output = await target.handle_message(
                message=message,
                user_id=user_id,
                llm_config=llm_config,
                history=history,
            )
        except Exception as exc:
            logger.warning(f"AnxinAssistant 单派发到 {persona_id} 失败: {exc}")
            return (
                f"已尝试转给 **{PERSONA_DISPLAY_NAME.get(persona_id, persona_id)}**，"
                f"但执行时出错：{exc}。建议换个说法或稍后重试。"
            )
        # 在前面加一行「来自 X」标识，保持透明
        prefix = f"> 来自 @{persona_id}（{PERSONA_DISPLAY_NAME.get(persona_id, persona_id)}）\n\n"
        return prefix + (output or "")

    # ------------------------------------------------------------------
    # 兼容 specialized agent 的 process()（覆盖父类，加 metadata）
    # ------------------------------------------------------------------
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        message = task.get("description") or task.get("message") or ""
        context = task.get("context") or {}
        content = await self.handle_message(
            message=message,
            user_id=context.get("user_id"),
            llm_config=context.get("llm_config"),
            history=context.get("history"),
            extra=context,
        )
        return AgentResponse(
            agent_name=self.name,
            content=content,
            metadata={
                "persona_id": self.persona_id,
                "capabilities": list(self.capabilities),
                "is_orchestrator": True,
            },
        )

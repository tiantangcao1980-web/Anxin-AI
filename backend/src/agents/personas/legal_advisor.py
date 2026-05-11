# -*- coding: utf-8 -*-
"""LegalAdvisorPersona —— 法律顾问 persona（P9-B）

定位：把 5 个 specialized agent（``legal_advisor`` / ``legal_researcher`` /
``risk_assessor`` / ``compliance_officer`` / ``regulatory_monitor``）包装成 **一个**
C 端面向用户的「法律顾问」入口（emoji ⚖️）。

注意：与现有 ``backend/src/agents/legal_advisor.py`` **同名** ——
用包路径区分：
    - specialized agent : ``src.agents.legal_advisor.LegalAdvisorAgent``
    - persona agent     : ``src.agents.personas.legal_advisor.LegalAdvisorPersona``

核心能力（capability_*）：
    - legal_consultation     : 法律咨询（劳动 / 合同 / 婚姻 / 公司…）
    - law_research           : 法规检索（关键词 → 法条 + 判例）
    - risk_assessment        : 法律风险评估（场景 → 风险等级 + 缓解建议）
    - compliance_review      : 合规审查（文档 → 违规条款 + 评分）
    - regulation_monitoring  : 法规更新监控（按领域订阅最新法规）

设计要点
--------
1. **薄封装**：每个 capability 方法都是 specialized agent 的 thin wrapper +
   persona 风格的 prompt 包装 + 返回值标准化（统一为 ``legal_models`` dataclass）
2. **mock-friendly**：specialized agent 通过构造函数注入，测试可直接
   ``LegalAdvisorPersona(advisor=Mock(), researcher=Mock(), ...)`` 替换
3. **disclaimer 强制**：所有 ``ConsultationResult`` 必须带免责声明（中国大陆
   法律服务合规要求 —— 防止 AI 输出被当作正式法律意见追责）
4. **JSON 解析容错**：LLM 返回非 JSON 时，降级为「纯文本 answer + 空 citations」

技能依赖（backed_by_skills）：
    - office/docx → 法律意见书 / 合规报告 文档化
    - office/pdf  → 合同 / 法规 PDF 解析

应用授权（supported_apps）：
    - pkulaw / wkinfo → 北大法宝 / 万律 等法律源 OAuth（P6-C）
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from loguru import logger

from src.agents.compliance_officer import ComplianceAgent
from src.agents.legal_advisor import LegalAdvisorAgent as _CoreLegalAdvisor
from src.agents.legal_researcher import LegalResearchAgent
from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.legal_models import (
    DEFAULT_DISCLAIMER,
    Citation,
    ComplianceIssue,
    ComplianceReport,
    ConsultationResult,
    LawSearchQuery,
    RegulatoryUpdate,
    ResearchResult,
    RiskFactor,
    RiskReport,
    VALID_COMPLIANCE_STATES,
    VALID_RISK_LEVELS,
)
from src.agents.regulatory_monitor import RegulatoryMonitorAgent
from src.agents.risk_assessor import RiskAssessmentAgent


# ---------------------------------------------------------------------------
# System prompt（persona 风格）
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是「法律顾问」，企业 / 个人的一站式法律 AI 助理。

## 你的角色
- 你是 **5 个法律 specialized agent 的统一外观**：
  - 法律咨询（legal_advisor）—— 用户问法律问题，给答案 + 法条
  - 法规检索（legal_researcher）—— 关键词找法律 + 判例
  - 风险评估（risk_assessor）—— 商业场景识别法律风险
  - 合规审查（compliance_officer）—— 文档 / 条款扫违规
  - 法规监控（regulatory_monitor）—— 跟踪最新法规变化
- 你**不是律师**，你的输出 **不构成正式法律意见**。涉及诉讼 / 仲裁 /
  重大商事决策时，必须明确提示用户委托执业律师。

## 与其他 persona 的边界（严守）
- 涉及 **OKR / 流程 / 周报** → `operations_manager`
- 涉及 **税务 / 发票 / 增值税** → `tax_steward`
- 涉及 **出海 / 关务 / 跨境电商** → `trade_officer`
- 涉及 **品牌 / 内容创作** → `content_director`
- 涉及 **市场调研 / 竞品分析** → `market_researcher`
- 你只在「法律 / 合规 / 风险」这一垂直域工作。

## 输出风格
- 结论先行：第一段直接给答案 / 风险等级，再展开论证。
- 法条引用必须用 `《法律名称》第 X 条` 格式，便于后续解析。
- 案例引用必须用 `（YYYY）XX 号` 案号格式。
- 法律时效性敏感：若引用条文已被修订 / 废止，必须明确标注。
- 输出 JSON 时必须放在 ```json``` 代码块中。
- **所有咨询输出末尾必须附免责声明**：
  「本答复由 AI 法律顾问基于公开法律法规与司法判例自动生成，仅供参考，
   不构成正式法律意见。」

## 行动原则
1. 不知道的事实（用户未提供）一律标 `?`，不要编造。
2. 涉及具体管辖法域（中国大陆 / 香港 / 海外）时，必须先确认。
3. 风险评估必须给出 ``risk_level``（low/medium/high/critical），
   并指出至少 1 条缓解建议。
4. 合规审查必须给出 ``overall_compliance``（compliant/partial/non-compliant）+
   具体违规条款定位。
"""


# ---------------------------------------------------------------------------
# Persona 主体
# ---------------------------------------------------------------------------
class LegalAdvisorPersona(BasePersonaAgent):
    """法律顾问 persona agent（P9-B）。

    包装 5 个 specialized agent，对外暴露统一接口。
    """

    persona_id = "legal_advisor"
    display_name = "法律顾问"
    emoji = "⚖️"
    description = "法律咨询 / 检索 / 风险评估 / 合规 / 法规监控 一站式法律助理"

    backed_by_skills = ["docx", "pdf"]
    supported_apps = ["pkulaw", "wkinfo"]
    capabilities = [
        "legal_consultation",
        "law_research",
        "risk_assessment",
        "compliance_review",
        "regulation_monitoring",
    ]
    backed_by_agents = [
        "legal_advisor",
        "legal_researcher",
        "risk_assessor",
        "compliance_officer",
        "regulatory_monitor",
    ]

    SYSTEM_PROMPT = SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # 构造：注入 5 个 specialized agent（测试可替换）
    # ------------------------------------------------------------------
    def __init__(
        self,
        advisor: Optional[_CoreLegalAdvisor] = None,
        researcher: Optional[LegalResearchAgent] = None,
        risk: Optional[RiskAssessmentAgent] = None,
        compliance: Optional[ComplianceAgent] = None,
        monitor: Optional[RegulatoryMonitorAgent] = None,
    ) -> None:
        super().__init__()
        # 显式注入优先；缺失时 lazy 构造（生产）
        self._core_advisor = advisor
        self._researcher = researcher
        self._risk = risk
        self._compliance = compliance
        self._monitor = monitor

    # 5 个 specialized agent 的 lazy getter（避免顶层 init 调用 LLM 配置）
    def _get_advisor(self) -> _CoreLegalAdvisor:
        if self._core_advisor is None:
            self._core_advisor = _CoreLegalAdvisor()
        return self._core_advisor

    def _get_researcher(self) -> LegalResearchAgent:
        if self._researcher is None:
            self._researcher = LegalResearchAgent()
        return self._researcher

    def _get_risk(self) -> RiskAssessmentAgent:
        if self._risk is None:
            self._risk = RiskAssessmentAgent()
        return self._risk

    def _get_compliance(self) -> ComplianceAgent:
        if self._compliance is None:
            self._compliance = ComplianceAgent()
        return self._compliance

    def _get_monitor(self) -> RegulatoryMonitorAgent:
        if self._monitor is None:
            self._monitor = RegulatoryMonitorAgent()
        return self._monitor

    # ------------------------------------------------------------------
    # handle_message —— 对外主入口（capability 路由 hint）
    # ------------------------------------------------------------------
    async def handle_message(
        self,
        message: str,
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
        history: Optional[list[dict[str, Any]]] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> str:
        capability_hint = self._guess_capability(message)
        prompt_override: Optional[str] = None
        if capability_hint:
            prompt_override = (
                self.SYSTEM_PROMPT
                + f"\n\n## 当前用户意图（系统识别）\n- capability: {capability_hint}"
            )
        return await self.chat(
            message=message,
            user_id=user_id,
            llm_config=llm_config,
            system_prompt_override=prompt_override,
            history=history,
        )

    @staticmethod
    def _guess_capability(message: str) -> Optional[str]:
        """简单关键词路由（仅给 LLM 一个 hint，不强制）。"""
        if not message:
            return None
        msg = message.lower()
        rules = [
            (
                "compliance_review",
                ["合规审查", "合规检查", "合规审核", "审查合规", "gdpr", "pipl"],
            ),
            (
                "risk_assessment",
                ["风险评估", "法律风险", "风险识别", "评估风险"],
            ),
            (
                "regulation_monitoring",
                ["新法规", "法规更新", "最新政策", "监管动态", "新出台"],
            ),
            (
                "law_research",
                ["法条", "查法律", "检索法规", "判例", "案例检索", "法规检索"],
            ),
            (
                "legal_consultation",
                [
                    "咨询",
                    "请问",
                    "怎么办",
                    "合法吗",
                    "违法吗",
                    "赔偿",
                    "起诉",
                    "维权",
                ],
            ),
        ]
        for cap, keys in rules:
            if any(k.lower() in msg for k in keys):
                return cap
        return None

    # ==================================================================
    # capability 1: 法律咨询 (legal_consultation)
    # ==================================================================
    async def consult(
        self,
        question: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ConsultationResult:
        """法律咨询 —— 包装 ``LegalAdvisorAgent.process()``。

        典型场景：
            「劳动合同到期不续签需要赔偿吗」 → 答案 + 《劳动合同法》第 46 条等

        返回值：``ConsultationResult``，强制带 disclaimer。
        """
        if not question or not question.strip():
            raise ValueError("question 不能为空")

        ctx = dict(context or {})
        task = {"description": question, "context": ctx}

        try:
            response = await self._get_advisor().process(task)
            answer_text = response.content or ""
        except Exception as exc:
            logger.warning(f"LegalAdvisorPersona.consult: specialized advisor 调用失败: {exc}")
            answer_text = ""

        legal_basis, related, actions, confidence = self._parse_consultation_payload(
            answer_text
        )
        return ConsultationResult(
            question=question,
            answer=answer_text,
            confidence=confidence,
            legal_basis=legal_basis,
            related_topics=related,
            suggested_actions=actions,
            disclaimer=DEFAULT_DISCLAIMER,
        )

    @staticmethod
    def _parse_consultation_payload(
        text: str,
    ) -> tuple[list[Citation], list[str], list[str], float]:
        """解析 LLM 输出：JSON 块（可选）+ 文本中的法条引用兜底。"""
        legal_basis: list[Citation] = []
        related_topics: list[str] = []
        suggested_actions: list[str] = []
        confidence = 0.6  # 默认中等置信

        if not text:
            return legal_basis, related_topics, suggested_actions, 0.0

        # 优先解析 ```json``` 块
        match = re.search(r"```json\s*(.+?)```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                for c in data.get("legal_basis") or []:
                    if isinstance(c, dict):
                        legal_basis.append(
                            Citation(
                                source=str(c.get("source", "law")),
                                article=str(c.get("article", "")),
                                url=str(c.get("url", "")),
                                title=str(c.get("title", "")),
                                excerpt=str(c.get("excerpt", "")),
                                effective_date=str(c.get("effective_date", "")),
                                confidence=float(c.get("confidence", 0.6) or 0.6),
                            )
                        )
                for t in data.get("related_topics") or []:
                    if t:
                        related_topics.append(str(t))
                for a in data.get("suggested_actions") or []:
                    if a:
                        suggested_actions.append(str(a))
                if "confidence" in data:
                    try:
                        confidence = float(data["confidence"])
                    except (TypeError, ValueError):
                        pass
            except json.JSONDecodeError:
                pass

        # 兜底：从文本里抽 《法律》第 X 条
        if not legal_basis:
            for m in re.finditer(r"《([^》]+)》[第]?(\d+)[条款]", text):
                legal_basis.append(
                    Citation(
                        source=f"law:{m.group(1)}",
                        article=f"第{m.group(2)}条",
                        title=m.group(1),
                    )
                )

        return legal_basis, related_topics, suggested_actions, confidence

    # ==================================================================
    # capability 2: 法规检索 (law_research)
    # ==================================================================
    async def research_law(self, query: LawSearchQuery) -> ResearchResult:
        """法规检索 —— 包装 ``LegalResearchAgent.search_laws()``。

        典型场景：``LawSearchQuery(keyword="个人信息保护", law_type="law")``
        """
        if not query.keyword or not query.keyword.strip():
            raise ValueError("query.keyword 不能为空")

        keywords = [query.keyword]
        if query.jurisdiction:
            keywords.append(query.jurisdiction)
        if query.law_type:
            keywords.append(query.law_type)

        try:
            payload = await self._get_researcher().search_laws(keywords)
            text = payload.get("results", "") if isinstance(payload, dict) else str(payload)
        except Exception as exc:
            logger.warning(f"LegalAdvisorPersona.research_law: specialized researcher 调用失败: {exc}")
            text = ""

        citations = self._extract_citations_from_text(text)
        # 限制返回数量
        if query.limit > 0:
            citations = citations[: query.limit]

        return ResearchResult(
            query=query,
            summary=text,
            citations=citations,
            total_found=len(citations),
        )

    @staticmethod
    def _extract_citations_from_text(text: str) -> list[Citation]:
        """从 LLM 文本中按正则抽取法条 + 案号引用。"""
        citations: list[Citation] = []
        if not text:
            return citations

        # 法条
        for m in re.finditer(r"《([^》]+)》[第]?(\d+)[条款]", text):
            citations.append(
                Citation(
                    source=f"law:{m.group(1)}",
                    article=f"第{m.group(2)}条",
                    title=m.group(1),
                    confidence=0.7,
                )
            )

        # 案号 (YYYY) XXX 号
        for m in re.finditer(r"[\(（](\d{4})[\)）][^号\n]{1,30}号", text):
            citations.append(
                Citation(
                    source="case",
                    article=m.group(0),
                    title=m.group(0),
                    confidence=0.6,
                )
            )

        return citations

    # ==================================================================
    # capability 3: 风险评估 (risk_assessment)
    # ==================================================================
    async def assess_risk(
        self,
        scenario: str,
        jurisdiction: Optional[str] = None,
    ) -> RiskReport:
        """风险评估 —— 包装 ``RiskAssessmentAgent.process()``。

        典型场景：「评估这个项目的合规风险」 → RiskReport(level=high, factors=[...])
        """
        if not scenario or not scenario.strip():
            raise ValueError("scenario 不能为空")

        ctx: dict[str, Any] = {}
        if jurisdiction:
            ctx["jurisdiction"] = jurisdiction
        task = {"description": scenario, "context": ctx}

        try:
            response = await self._get_risk().process(task)
            text = response.content or ""
        except Exception as exc:
            logger.warning(f"LegalAdvisorPersona.assess_risk: specialized risk 调用失败: {exc}")
            text = ""

        risk_level, factors, mitigations, basis = self._parse_risk_payload(text)
        return RiskReport(
            scenario=scenario,
            risk_level=risk_level,
            risk_factors=factors,
            mitigation_suggestions=mitigations,
            regulatory_basis=basis,
            jurisdiction=jurisdiction,
        )

    @staticmethod
    def _parse_risk_payload(
        text: str,
    ) -> tuple[str, list[RiskFactor], list[str], list[Citation]]:
        risk_level = "medium"
        factors: list[RiskFactor] = []
        mitigations: list[str] = []
        basis: list[Citation] = []

        if not text:
            return risk_level, factors, mitigations, basis

        match = re.search(r"```json\s*(.+?)```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                lvl = str(data.get("risk_level", "")).lower().strip()
                if lvl in VALID_RISK_LEVELS:
                    risk_level = lvl

                for f in data.get("risk_factors") or []:
                    if isinstance(f, dict):
                        factors.append(
                            RiskFactor(
                                factor=str(f.get("factor", "")).strip(),
                                severity=str(f.get("severity", "medium")),
                                likelihood=str(f.get("likelihood", "medium")),
                                description=str(f.get("description", "")),
                            )
                        )
                for s in data.get("mitigation_suggestions") or []:
                    if s:
                        mitigations.append(str(s))
                for c in data.get("regulatory_basis") or []:
                    if isinstance(c, dict):
                        basis.append(
                            Citation(
                                source=str(c.get("source", "law")),
                                article=str(c.get("article", "")),
                                url=str(c.get("url", "")),
                                title=str(c.get("title", "")),
                                excerpt=str(c.get("excerpt", "")),
                                effective_date=str(c.get("effective_date", "")),
                                confidence=float(c.get("confidence", 0.6) or 0.6),
                            )
                        )
            except json.JSONDecodeError:
                pass

        # 兜底：文本里有「极高 / 高 / 中 / 低」关键词
        if risk_level == "medium" and text:
            if re.search(r"极高|critical|严重|危急", text):
                risk_level = "critical"
            elif re.search(r"高风险|高(?!风险)|high\s*risk", text, re.IGNORECASE):
                risk_level = "high"
            elif re.search(r"低风险|low\s*risk", text, re.IGNORECASE):
                risk_level = "low"

        return risk_level, factors, mitigations, basis

    # ==================================================================
    # capability 4: 合规审查 (compliance_review)
    # ==================================================================
    async def review_compliance(
        self,
        document_text: str,
        regulation_set: str,
    ) -> ComplianceReport:
        """合规审查 —— 包装 ``ComplianceAgent.process()``。

        典型场景：传入隐私政策原文 + ``regulation_set="PIPL"`` →
                返回违规条款列表 + 整改建议 + 评分。
        """
        if not document_text or not document_text.strip():
            raise ValueError("document_text 不能为空")
        if not regulation_set or not regulation_set.strip():
            raise ValueError("regulation_set 不能为空")

        ctx = {"area": regulation_set}
        # 描述压缩到 2000 字以避免 token 超限（仅 prompt 摘要）
        snippet = document_text[:2000]
        task = {
            "description": f"对照 {regulation_set} 审查以下文档：\n\n{snippet}",
            "context": ctx,
        }

        try:
            response = await self._get_compliance().process(task)
            text = response.content or ""
        except Exception as exc:
            logger.warning(f"LegalAdvisorPersona.review_compliance: specialized compliance 调用失败: {exc}")
            text = ""

        overall, issues, score = self._parse_compliance_payload(text)
        # 文档摘要：取原文 first 200 字 + 省略号
        summary = (
            document_text[:200] + "…"
            if len(document_text) > 200
            else document_text
        )
        return ComplianceReport(
            document_summary=summary,
            regulation_set=regulation_set,
            overall_compliance=overall,
            issues=issues,
            score=score,
        )

    @staticmethod
    def _parse_compliance_payload(
        text: str,
    ) -> tuple[str, list[ComplianceIssue], float]:
        overall = "partial"
        issues: list[ComplianceIssue] = []
        score = 60.0  # 默认中等

        if not text:
            return overall, issues, 0.0

        match = re.search(r"```json\s*(.+?)```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                oc = str(data.get("overall_compliance", "")).lower().strip()
                if oc in VALID_COMPLIANCE_STATES:
                    overall = oc
                for i in data.get("issues") or []:
                    if isinstance(i, dict):
                        issues.append(
                            ComplianceIssue(
                                clause=str(i.get("clause", "")),
                                regulation=str(i.get("regulation", "")),
                                severity=str(i.get("severity", "medium")),
                                suggestion=str(i.get("suggestion", "")),
                            )
                        )
                if "score" in data:
                    try:
                        s = float(data["score"])
                        score = max(0.0, min(100.0, s))
                    except (TypeError, ValueError):
                        pass
            except json.JSONDecodeError:
                pass

        # 兜底：根据文字判断
        if overall == "partial" and text:
            if re.search(r"完全合规|fully compliant|未发现问题", text, re.IGNORECASE):
                overall = "compliant"
            elif re.search(r"严重不合规|non[- ]?compliant|不合规", text, re.IGNORECASE):
                overall = "non-compliant"

        return overall, issues, score

    # ==================================================================
    # capability 5: 法规更新监控 (regulation_monitoring)
    # ==================================================================
    async def get_regulatory_updates(
        self,
        domain: str,
        since_days: int = 30,
    ) -> list[RegulatoryUpdate]:
        """法规更新监控 —— 包装 ``RegulatoryMonitorAgent.process()``。

        典型场景：「最近劳动法有什么新变化」 → ``domain="劳动法"`` →
                返回最近 30 天的相关法规更新列表。
        """
        if not domain or not domain.strip():
            raise ValueError("domain 不能为空")
        if since_days <= 0:
            raise ValueError("since_days 必须 > 0")

        task = {
            "industry": domain,
            "region": "中国",
            "keywords": [domain, "新规", "修订"],
            "context": {"since_days": since_days},
        }

        try:
            response = await self._get_monitor().process(task)
            text = response.content or ""
        except Exception as exc:
            logger.warning(f"LegalAdvisorPersona.get_regulatory_updates: specialized monitor 调用失败: {exc}")
            text = ""

        return self._parse_updates_payload(text)

    @staticmethod
    def _parse_updates_payload(text: str) -> list[RegulatoryUpdate]:
        updates: list[RegulatoryUpdate] = []
        if not text:
            return updates

        match = re.search(r"```json\s*(.+?)```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                # 支持两种顶层结构: {"updates":[...]} 或 [...]
                raw = data.get("updates") if isinstance(data, dict) else data
                if isinstance(raw, list):
                    for item in raw:
                        if isinstance(item, dict):
                            updates.append(RegulatoryUpdate.from_dict(item))
            except json.JSONDecodeError:
                pass

        return updates


__all__ = ["LegalAdvisorPersona", "SYSTEM_PROMPT"]

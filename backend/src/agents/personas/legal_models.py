"""法律顾问 persona（P9-B）输出物的统一数据模型。

设计原则：
    - **可序列化**：所有字段都是 stdlib 基本类型，方便经 Pydantic 镜像后
      送到 API 层（``api/routes/schemas/persona_legal.py``）
    - **可审计**：``Citation`` 字段保留法条 / 案例的源链接 + 原文片段，
      便于法务复核与责任溯源
    - **可分级**：``RiskReport.risk_level`` 与 ``ComplianceReport.overall_compliance``
      使用受控枚举字符串，方便前端按颜色 / 优先级渲染
    - **可免责**：``ConsultationResult.disclaimer`` 是强制字段 —— 在中国
      法律服务领域，AI 输出必须明确「不构成正式法律意见」，避免合规风险
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import uuid4

# ---------------------------------------------------------------------------
# 共用：法律引文
# ---------------------------------------------------------------------------


@dataclass
class Citation:
    """单条法律引用 / 证据。

    与 ``research_models.Citation`` 类似，但语义偏 **法律**：
        - ``source``    —— 来源标识，如 ``law:劳动合同法`` / ``case:(2024)京01民终123号``
                           / ``regulation:个人信息保护法`` / ``judicial_interpretation``
        - ``article``   —— 法条号 / 案号（``law`` 类型时填条款号；``case`` 类型填案号）
        - ``url``       —— 原文链接（pkulaw / wkinfo / 国家法律法规数据库）
        - ``title``     —— 法律 / 案例 标题
        - ``excerpt``   —— 真实条文摘录（**禁止改写**）
        - ``effective_date`` —— 生效日期（ISO 字符串），用于时效性判断
        - ``confidence`` —— 0-1，模型对该引文与问题相关性的自评
    """

    source: str
    article: str = ""
    url: str = ""
    title: str = ""
    excerpt: str = ""
    effective_date: str = ""  # ISO format YYYY-MM-DD; 空字符串 = 未知
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "article": self.article,
            "url": self.url,
            "title": self.title,
            "excerpt": self.excerpt,
            "effective_date": self.effective_date,
            "confidence": float(self.confidence),
        }


# ---------------------------------------------------------------------------
# capability 1: 法律咨询
# ---------------------------------------------------------------------------


# 标准免责声明 —— 强制注入到每条 ConsultationResult，避免被解读为正式法律意见
DEFAULT_DISCLAIMER = (
    "本答复由 AI 法律顾问基于公开法律法规与司法判例自动生成，仅供参考，"
    "不构成正式法律意见。涉及具体诉讼 / 仲裁 / 重大商事决策时，"
    "请委托具有执业资格的律师出具正式意见。"
)


@dataclass
class ConsultationResult:
    """法律咨询结果。

    典型场景：用户问「劳动合同到期不续签需要赔偿吗」，返回的就是这个。
    """

    question: str
    answer: str
    confidence: float = 0.0
    legal_basis: list[Citation] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    disclaimer: str = DEFAULT_DISCLAIMER
    consultation_id: str = field(default_factory=lambda: uuid4().hex)
    created_ts: float = field(default_factory=time.time)
    persona_id: str = "legal_advisor"

    def to_dict(self) -> dict[str, Any]:
        return {
            "consultation_id": self.consultation_id,
            "persona_id": self.persona_id,
            "question": self.question,
            "answer": self.answer,
            "confidence": float(self.confidence),
            "legal_basis": [c.to_dict() for c in self.legal_basis],
            "related_topics": list(self.related_topics),
            "suggested_actions": list(self.suggested_actions),
            "disclaimer": self.disclaimer,
            "created_ts": float(self.created_ts),
        }


# ---------------------------------------------------------------------------
# capability 2: 法规检索
# ---------------------------------------------------------------------------


@dataclass
class LawSearchQuery:
    """法律法规检索查询参数。

    字段说明：
        - ``keyword``         —— 必填，检索关键词
        - ``law_type``        —— 法律类型筛选：``law`` / ``regulation``
                                  / ``judicial_interpretation`` / ``departmental_rule``
                                  / ``local_regulation`` / ``case``
        - ``jurisdiction``    —— 法域：``national`` / 省份名 / ``foreign``
        - ``effective_after`` —— 仅返回 此日期之后 生效的法规
        - ``limit``           —— 返回条数上限（默认 20）
    """

    keyword: str
    law_type: str | None = None
    jurisdiction: str | None = None
    effective_after: str | None = None  # ISO YYYY-MM-DD
    limit: int = 20

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "law_type": self.law_type,
            "jurisdiction": self.jurisdiction,
            "effective_after": self.effective_after,
            "limit": int(self.limit),
        }


@dataclass
class ResearchResult:
    """法规检索结果。"""

    query: LawSearchQuery
    summary: str = ""
    citations: list[Citation] = field(default_factory=list)
    total_found: int = 0
    research_id: str = field(default_factory=lambda: uuid4().hex)
    created_ts: float = field(default_factory=time.time)
    persona_id: str = "legal_advisor"

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_id": self.research_id,
            "persona_id": self.persona_id,
            "query": self.query.to_dict(),
            "summary": self.summary,
            "citations": [c.to_dict() for c in self.citations],
            "total_found": int(self.total_found),
            "created_ts": float(self.created_ts),
        }


# ---------------------------------------------------------------------------
# capability 3: 风险评估
# ---------------------------------------------------------------------------


# 受控字面量（前端按色阶渲染：low=绿 / medium=黄 / high=橙 / critical=红）
VALID_RISK_LEVELS = ("low", "medium", "high", "critical")


@dataclass
class RiskFactor:
    """单条风险因子。

    字段说明：
        - ``factor``      —— 风险点名称（"违约金条款约定不明"）
        - ``severity``    —— 严重程度：``low`` / ``medium`` / ``high`` / ``critical``
        - ``likelihood``  —— 发生概率：``low`` / ``medium`` / ``high``
        - ``description`` —— 详细分析
    """

    factor: str
    severity: str = "medium"
    likelihood: str = "medium"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": self.factor,
            "severity": self.severity,
            "likelihood": self.likelihood,
            "description": self.description,
        }


@dataclass
class RiskReport:
    """风险评估报告。"""

    scenario: str
    risk_level: str = "medium"  # 必须 ∈ VALID_RISK_LEVELS
    risk_factors: list[RiskFactor] = field(default_factory=list)
    mitigation_suggestions: list[str] = field(default_factory=list)
    regulatory_basis: list[Citation] = field(default_factory=list)
    jurisdiction: str | None = None
    report_id: str = field(default_factory=lambda: uuid4().hex)
    created_ts: float = field(default_factory=time.time)
    persona_id: str = "legal_advisor"

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "persona_id": self.persona_id,
            "scenario": self.scenario,
            "risk_level": self.risk_level,
            "risk_factors": [f.to_dict() for f in self.risk_factors],
            "mitigation_suggestions": list(self.mitigation_suggestions),
            "regulatory_basis": [c.to_dict() for c in self.regulatory_basis],
            "jurisdiction": self.jurisdiction,
            "created_ts": float(self.created_ts),
        }


# ---------------------------------------------------------------------------
# capability 4: 合规审查
# ---------------------------------------------------------------------------


# 受控字面量
VALID_COMPLIANCE_STATES = ("compliant", "partial", "non-compliant")


@dataclass
class ComplianceIssue:
    """单条合规问题。

    字段说明：
        - ``clause``     —— 原文条款（或位置定位）
        - ``regulation`` —— 违反的法规（"GDPR Art. 6" / "个人信息保护法 第13条"）
        - ``severity``   —— ``low`` / ``medium`` / ``high`` / ``critical``
        - ``suggestion`` —— 整改建议
    """

    clause: str
    regulation: str = ""
    severity: str = "medium"
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause": self.clause,
            "regulation": self.regulation,
            "severity": self.severity,
            "suggestion": self.suggestion,
        }


@dataclass
class ComplianceReport:
    """合规审查报告。"""

    document_summary: str
    regulation_set: str  # "GDPR" / "PIPL" / "劳动法" / "个人信息保护法" / ...
    overall_compliance: str = "partial"  # 必须 ∈ VALID_COMPLIANCE_STATES
    issues: list[ComplianceIssue] = field(default_factory=list)
    score: float = 0.0  # 0-100
    report_id: str = field(default_factory=lambda: uuid4().hex)
    created_ts: float = field(default_factory=time.time)
    persona_id: str = "legal_advisor"

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "persona_id": self.persona_id,
            "document_summary": self.document_summary,
            "regulation_set": self.regulation_set,
            "overall_compliance": self.overall_compliance,
            "issues": [i.to_dict() for i in self.issues],
            "score": float(self.score),
            "created_ts": float(self.created_ts),
        }


# ---------------------------------------------------------------------------
# capability 5: 法规更新监控
# ---------------------------------------------------------------------------


@dataclass
class RegulatoryUpdate:
    """法规更新条目。"""

    title: str
    issuing_authority: str = ""
    issued_date: str | None = None  # ISO YYYY-MM-DD
    effective_date: str | None = None  # ISO YYYY-MM-DD; None = 待生效
    summary: str = ""
    impact_assessment: str = ""
    affected_domains: list[str] = field(default_factory=list)
    full_text_url: str = ""
    update_id: str = field(default_factory=lambda: uuid4().hex)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegulatoryUpdate:
        """从 LLM JSON 输出构造（兼容字段缺失）。"""

        def _iso(v: Any) -> str | None:
            if not v:
                return None
            if isinstance(v, date):
                return v.isoformat()
            return str(v)

        affected = data.get("affected_domains") or []
        if not isinstance(affected, list):
            affected = []
        return cls(
            title=str(data.get("title", "")).strip(),
            issuing_authority=str(data.get("issuing_authority", "")).strip(),
            issued_date=_iso(data.get("issued_date")),
            effective_date=_iso(data.get("effective_date")),
            summary=str(data.get("summary", "")).strip(),
            impact_assessment=str(data.get("impact_assessment", "")).strip(),
            affected_domains=[str(x) for x in affected if x],
            full_text_url=str(data.get("full_text_url", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "update_id": self.update_id,
            "title": self.title,
            "issuing_authority": self.issuing_authority,
            "issued_date": self.issued_date,
            "effective_date": self.effective_date,
            "summary": self.summary,
            "impact_assessment": self.impact_assessment,
            "affected_domains": list(self.affected_domains),
            "full_text_url": self.full_text_url,
        }


__all__ = [
    "Citation",
    "ConsultationResult",
    "LawSearchQuery",
    "ResearchResult",
    "RiskFactor",
    "RiskReport",
    "ComplianceIssue",
    "ComplianceReport",
    "RegulatoryUpdate",
    "DEFAULT_DISCLAIMER",
    "VALID_RISK_LEVELS",
    "VALID_COMPLIANCE_STATES",
]

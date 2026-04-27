# -*- coding: utf-8 -*-
"""persona_dd 路由 Pydantic schemas（请求 / 响应 DTO）。

P9-D 尽调专家 persona 对外 API 的 IO 类型；与 ``personas/dd_models.py``
的 dataclass 一一对应。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 通用：引文（与 persona_market 共享语义；这里独立声明避免跨 module 耦合）
# ---------------------------------------------------------------------------


class CitationOut(BaseModel):
    source: str
    url: str
    title: str = ""
    excerpt: str = ""
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# 公司尽调
# ---------------------------------------------------------------------------


class InvestigateCompanyIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    depth: Literal["quick", "standard", "deep"] = "standard"


class CompanyBasicInfoOut(BaseModel):
    name: str
    legal_representative: str
    registered_capital: float
    establishment_date: date
    business_scope: str
    industry: str
    address: str
    unified_credit_code: str
    status: str


class LitigationRecordOut(BaseModel):
    case_number: str
    case_type: str
    court: str
    role: str
    amount_disputed: float | None = None
    judgment_date: date | None = None
    judgment_summary: str = ""
    full_text_url: str = ""


class CreditFlagOut(BaseModel):
    flag_type: str
    description: str
    issued_date: date
    issuing_authority: str
    severity: str = "medium"


class DueDiligenceReportOut(BaseModel):
    report_id: str
    target: str
    target_type: str
    investigation_depth: str
    basic_info: CompanyBasicInfoOut | None = None
    shareholders: list[dict[str, Any]] = Field(default_factory=list)
    key_personnel: list[dict[str, Any]] = Field(default_factory=list)
    litigation_records: list[LitigationRecordOut] = Field(default_factory=list)
    credit_flags: list[CreditFlagOut] = Field(default_factory=list)
    intellectual_properties: list[dict[str, Any]] = Field(default_factory=list)
    public_news_count: int = 0
    overall_risk_level: str = "unknown"
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime
    citations: list[CitationOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 证据分析
# ---------------------------------------------------------------------------


class AnalyzeEvidenceIn(BaseModel):
    document_text: str = Field(min_length=1, max_length=200_000)
    claim: str = Field(min_length=1, max_length=2_000)


class EvidenceAnalysisOut(BaseModel):
    document_summary: str
    claim: str
    supports_claim: bool
    confidence: float
    supporting_excerpts: list[str] = Field(default_factory=list)
    contradicting_excerpts: list[str] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)
    authenticity_score: float = 0.5
    forgery_indicators: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 舆情监控
# ---------------------------------------------------------------------------


class MonitorSentimentIn(BaseModel):
    target: str = Field(min_length=1, max_length=200)
    sources: list[str] = Field(default_factory=list)
    lookback_days: int = Field(default=30, ge=1, le=365)


class SentimentReportOut(BaseModel):
    target: str
    period_start: date
    period_end: date
    overall_sentiment: str
    sentiment_score: float
    volume: int = 0
    by_source: dict[str, dict[str, Any]] = Field(default_factory=dict)
    top_topics: list[dict[str, Any]] = Field(default_factory=list)
    notable_events: list[dict[str, Any]] = Field(default_factory=list)
    trend: str = "stable"


# ---------------------------------------------------------------------------
# 关系图谱
# ---------------------------------------------------------------------------


class RelationshipGraphIn(BaseModel):
    entity: str = Field(min_length=1, max_length=200)
    depth: int = Field(default=2, ge=1, le=3)


class RelationshipNodeOut(BaseModel):
    id: str
    name: str
    type: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class RelationshipEdgeOut(BaseModel):
    from_id: str
    to_id: str
    relationship: str
    confidence: float = 0.8
    source: str = ""


class RelationshipGraphOut(BaseModel):
    root_entity: str
    nodes: list[RelationshipNodeOut] = Field(default_factory=list)
    edges: list[RelationshipEdgeOut] = Field(default_factory=list)
    depth: int = 0
    risk_paths: list[list[str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 风险评级
# ---------------------------------------------------------------------------


class GradeRiskIn(BaseModel):
    """以已生成的 dd_report 入参打分。

    传 ``report_id`` 命中缓存则免传 ``dd_report``；否则要求把完整报告传回。
    """

    report_id: str | None = None
    dd_report: DueDiligenceReportOut | None = None


class RiskGradeOut(BaseModel):
    grade: str
    score: float
    breakdown: dict[str, float] = Field(default_factory=dict)
    rationale: str = ""
    red_flags: list[str] = Field(default_factory=list)
    recommended_action: str = "monitor"


# ---------------------------------------------------------------------------
# 报告列表
# ---------------------------------------------------------------------------


class ListReportsOut(BaseModel):
    items: list[DueDiligenceReportOut] = Field(default_factory=list)
    total: int = 0

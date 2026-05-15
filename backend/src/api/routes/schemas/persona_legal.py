"""法律顾问 persona 路由的 Pydantic 镜像（P9-B）。

所有 In/Out 都对应 ``src.agents.personas.legal_models`` 中的数据类。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Output 子结构（对应 dataclass）
# ---------------------------------------------------------------------------


class CitationOut(BaseModel):
    source: str
    article: str = ""
    url: str = ""
    title: str = ""
    excerpt: str = ""
    effective_date: str = ""
    confidence: float = 0.5


class RiskFactorOut(BaseModel):
    factor: str
    severity: str = "medium"
    likelihood: str = "medium"
    description: str = ""


class ComplianceIssueOut(BaseModel):
    clause: str
    regulation: str = ""
    severity: str = "medium"
    suggestion: str = ""


# ---------------------------------------------------------------------------
# Outputs（顶层）
# ---------------------------------------------------------------------------


class ConsultationResultOut(BaseModel):
    consultation_id: str
    persona_id: str = "legal_advisor"
    question: str
    answer: str
    confidence: float = 0.0
    legal_basis: list[CitationOut] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    disclaimer: str
    created_ts: float = 0.0


class LawSearchQueryOut(BaseModel):
    keyword: str
    law_type: str | None = None
    jurisdiction: str | None = None
    effective_after: str | None = None
    limit: int = 20


class ResearchResultOut(BaseModel):
    research_id: str
    persona_id: str = "legal_advisor"
    query: LawSearchQueryOut
    summary: str = ""
    citations: list[CitationOut] = Field(default_factory=list)
    total_found: int = 0
    created_ts: float = 0.0


class RiskReportOut(BaseModel):
    report_id: str
    persona_id: str = "legal_advisor"
    scenario: str
    risk_level: str
    risk_factors: list[RiskFactorOut] = Field(default_factory=list)
    mitigation_suggestions: list[str] = Field(default_factory=list)
    regulatory_basis: list[CitationOut] = Field(default_factory=list)
    jurisdiction: str | None = None
    created_ts: float = 0.0


class ComplianceReportOut(BaseModel):
    report_id: str
    persona_id: str = "legal_advisor"
    document_summary: str
    regulation_set: str
    overall_compliance: str
    issues: list[ComplianceIssueOut] = Field(default_factory=list)
    score: float = 0.0
    created_ts: float = 0.0


class RegulatoryUpdateOut(BaseModel):
    update_id: str
    title: str
    issuing_authority: str = ""
    issued_date: str | None = None
    effective_date: str | None = None
    summary: str = ""
    impact_assessment: str = ""
    affected_domains: list[str] = Field(default_factory=list)
    full_text_url: str = ""


class RegulatoryUpdatesOut(BaseModel):
    domain: str
    since_days: int
    updates: list[RegulatoryUpdateOut] = Field(default_factory=list)
    total: int = 0


class LegalBasisExplainOut(BaseModel):
    """法条解释（GET /legal-basis-explain 返回）。"""

    law_id: str
    title: str = ""
    article: str = ""
    explanation: str = ""
    related_citations: list[CitationOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class ConsultIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    context: dict | None = Field(
        default=None,
        description="可选上下文，如 background / role / jurisdiction",
    )


class ResearchIn(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    law_type: str | None = Field(
        default=None,
        description="law / regulation / judicial_interpretation / departmental_rule / local_regulation / case",
    )
    jurisdiction: str | None = Field(default=None, max_length=100)
    effective_after: str | None = Field(
        default=None,
        description="ISO YYYY-MM-DD",
    )
    limit: int = Field(20, ge=1, le=100)


class AssessRiskIn(BaseModel):
    scenario: str = Field(..., min_length=1, max_length=4000)
    jurisdiction: str | None = Field(default=None, max_length=100)


class CheckComplianceIn(BaseModel):
    document_text: str = Field(..., min_length=1, max_length=200_000)
    regulation_set: str = Field(..., min_length=1, max_length=200)

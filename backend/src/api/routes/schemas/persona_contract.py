"""合同管家 persona 路由 Pydantic schemas（P9-C）。

与 ``src/agents/personas/contract_models.py`` 中 dataclass 一一对应。
API 层用 pydantic 是为了：

1. FastAPI 自动 OpenAPI / Swagger UI / 校验。
2. 字段约束（``perspective`` 限 enum 等）。
3. 与前端 TypeScript 类型保持单一事实来源。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# 1. draft
# ---------------------------------------------------------------------------
class PartyIn(BaseModel):
    role: str = Field("", max_length=50)
    name: str = Field("", max_length=200)
    type: str | None = None  # "natural" / "legal_entity" / "other"


class DraftContractIn(BaseModel):
    contract_type: str = Field(..., min_length=1, max_length=100)
    parties: list[PartyIn] = Field(..., min_length=1, max_length=10)
    terms: dict[str, Any] = Field(default_factory=dict)
    language: str = Field("zh", max_length=10)


class ContractDraftOut(BaseModel):
    contract_type: str
    title: str
    full_text: str
    sections: list[dict] = Field(default_factory=list)
    suggested_clauses: list[dict] = Field(default_factory=list)
    estimated_word_count: int = 0
    language: str = "zh"
    docx_template_path: str | None = None


# ---------------------------------------------------------------------------
# 2. review
# ---------------------------------------------------------------------------
class ReviewContractIn(BaseModel):
    document_text: str = Field(..., min_length=1)
    perspective: str = Field("buyer", description="buyer | seller | neutral")

    @field_validator("perspective")
    @classmethod
    def _check_perspective(cls, v: str) -> str:
        if v not in {"buyer", "seller", "neutral"}:
            raise ValueError("perspective 必须是 buyer / seller / neutral")
        return v


class ReviewIssueOut(BaseModel):
    clause_text: str
    issue_type: str
    severity: str
    description: str
    suggested_revision: str
    location: dict = Field(default_factory=dict)


class ReviewReportOut(BaseModel):
    overall_assessment: str
    perspective: str
    score: float
    issues: list[ReviewIssueOut] = Field(default_factory=list)
    missing_clauses: list[str] = Field(default_factory=list)
    redundant_clauses: list[str] = Field(default_factory=list)
    recommendation: str


# ---------------------------------------------------------------------------
# 3. identify-risks
# ---------------------------------------------------------------------------
class IdentifyRisksIn(BaseModel):
    document_text: str = Field(..., min_length=1)


class CitationOut(BaseModel):
    source: str
    url: str
    title: str = ""
    excerpt: str = ""
    confidence: float = 0.5


class RiskAnalysisOut(BaseModel):
    overall_risk_level: str
    risks: list[dict] = Field(default_factory=list)
    blacklist_clauses: list[str] = Field(default_factory=list)
    legal_basis: list[CitationOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 4. templates
# ---------------------------------------------------------------------------
class TemplateOut(BaseModel):
    template_id: str
    name: str
    contract_type: str
    description: str
    use_case: str = ""
    language: str = "zh"
    word_count: int = 0
    last_used: str | None = None
    download_url: str = ""


class TemplateListOut(BaseModel):
    items: list[TemplateOut] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# 5. compare-versions
# ---------------------------------------------------------------------------
class CompareVersionsIn(BaseModel):
    v1_text: str = Field(..., min_length=1)
    v2_text: str = Field(..., min_length=1)


class VersionDiffOut(BaseModel):
    v1_summary: str
    v2_summary: str
    additions: list[dict] = Field(default_factory=list)
    deletions: list[dict] = Field(default_factory=list)
    modifications: list[dict] = Field(default_factory=list)
    semantic_changes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. archive
# ---------------------------------------------------------------------------
class ArchiveIn(BaseModel):
    contract_id: str = Field(..., min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    retention_period_days: int | None = Field(None, ge=1, le=36500)


class ArchiveResultOut(BaseModel):
    contract_id: str
    archive_url: str
    metadata: dict = Field(default_factory=dict)
    archived_at: str
    retention_period_days: int


# ---------------------------------------------------------------------------
# 7. archives list
# ---------------------------------------------------------------------------
class ArchiveListOut(BaseModel):
    items: list[ArchiveResultOut] = Field(default_factory=list)
    total: int = 0


__all__ = [
    "PartyIn",
    "DraftContractIn",
    "ContractDraftOut",
    "ReviewContractIn",
    "ReviewIssueOut",
    "ReviewReportOut",
    "IdentifyRisksIn",
    "CitationOut",
    "RiskAnalysisOut",
    "TemplateOut",
    "TemplateListOut",
    "CompareVersionsIn",
    "VersionDiffOut",
    "ArchiveIn",
    "ArchiveResultOut",
    "ArchiveListOut",
]

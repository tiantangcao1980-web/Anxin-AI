"""市场研究员 persona 路由的 Pydantic 镜像（P7-B）。

所有 In/Out 都对应 ``src.agents.personas.research_models`` 中的数据类。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Output 子结构（对应 dataclass）
# ---------------------------------------------------------------------------


class CitationOut(BaseModel):
    source: str
    url: str
    title: str = ""
    excerpt: str = ""
    confidence: float = 0.0


class ResearchStepOut(BaseModel):
    step_id: int
    query: str
    rationale: str = ""
    findings: list[CitationOut] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    duration_ms: int = 0


class ResearchReportOut(BaseModel):
    report_id: str
    persona_id: str = "market_researcher"
    question: str
    summary: str = ""
    findings: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[CitationOut] = Field(default_factory=list)
    steps: list[ResearchStepOut] = Field(default_factory=list)
    confidence_score: float = 0.0
    duration_ms: int = 0
    suggested_actions: list[str] = Field(default_factory=list)
    created_ts: float = 0.0


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class InvestigateCompanyIn(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    depth: int = Field(2, ge=1, le=5, description="DeepResearch 迭代次数")


class CompetitorMonitorIn(BaseModel):
    competitors: list[str] = Field(..., min_length=1, max_length=20)
    aspects: list[str] | None = Field(
        default=None,
        description="监控维度，如 ['产品矩阵', '定价']；None=默认全部",
    )


class IndustryTrendsIn(BaseModel):
    industry: str = Field(..., min_length=1, max_length=200)
    lookback_days: int = Field(90, ge=7, le=365)


class DeepResearchIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    max_iterations: int = Field(5, ge=1, le=10)
    seed_queries: list[str] | None = Field(default=None, max_length=10)


# ---------------------------------------------------------------------------
# Composite Output
# ---------------------------------------------------------------------------


class CompetitorMonitorOut(BaseModel):
    """每个竞品名 → 报告。"""

    items: dict[str, ResearchReportOut]
    total: int


class IndustryTrendsOut(BaseModel):
    industry: str
    lookback_days: int
    report: ResearchReportOut
    axes: dict[str, list[CitationOut]] = Field(default_factory=dict)

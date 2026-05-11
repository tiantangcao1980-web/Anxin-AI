# -*- coding: utf-8 -*-
"""市场研究员（market_researcher）persona 路由 —— P7-B。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/market"`` 注册）::

    POST   /api/v1/personas/market/investigate-company    body: { company, depth }
    POST   /api/v1/personas/market/competitor-monitor     body: { competitors, aspects }
    POST   /api/v1/personas/market/industry-trends        body: { industry, lookback_days }
    POST   /api/v1/personas/market/deep-research          body: { question, max_iterations }
    GET    /api/v1/personas/market/research/{report_id}   读取已生成报告

设计说明：
    - **agent 单例**：进程内共用一个 ``MarketResearcherAgent``，依赖项
      （fetch / kb_search / llm）从 lazy import 注入；测试可通过
      ``set_agent_for_test()`` 替换
    - **不持久化**：报告在 agent 进程内 LRU 缓存（容量 100）
    - **鉴权**：复用全局 ``get_current_user_required``，不再做 persona 级 ACL
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.agents.personas.market_researcher import MarketResearcherAgent
from src.agents.personas.research_models import (
    Citation,
    ResearchReport,
    ResearchStep,
)
from src.api.routes.schemas.persona_market import (
    CitationOut,
    CompetitorMonitorIn,
    CompetitorMonitorOut,
    DeepResearchIn,
    IndustryTrendsIn,
    IndustryTrendsOut,
    InvestigateCompanyIn,
    ResearchReportOut,
    ResearchStepOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# 单例 + 测试钩子
# ---------------------------------------------------------------------------

_agent: MarketResearcherAgent | None = None


def get_market_agent() -> MarketResearcherAgent:
    """获取（懒构造）全局 ``MarketResearcherAgent``。

    生产部署里应在 app 启动时显式注入 fetch / llm callable；这里给出
    一个「无依赖」可跑的兜底版本（fetch 仍然可用，因为 ``fetch_service``
    是全局单例）。
    """
    global _agent
    if _agent is None:
        try:
            from src.services.fetch import fetch_service as _fetch
        except Exception:
            _fetch = None
        _agent = MarketResearcherAgent(fetch_service=_fetch)
    return _agent


def set_agent_for_test(agent: MarketResearcherAgent | None) -> None:
    """单测专用：替换 / 重置全局 agent。"""
    global _agent
    _agent = agent


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------


def _ser_citation(c: Citation) -> CitationOut:
    return CitationOut(**c.to_dict())


def _ser_step(s: ResearchStep) -> ResearchStepOut:
    return ResearchStepOut(
        step_id=s.step_id,
        query=s.query,
        rationale=s.rationale,
        findings=[_ser_citation(c) for c in s.findings],
        next_questions=list(s.next_questions),
        duration_ms=s.duration_ms,
    )


def _ser_report(r: ResearchReport) -> ResearchReportOut:
    return ResearchReportOut(
        report_id=r.report_id,
        persona_id=r.persona_id,
        question=r.question,
        summary=r.summary,
        findings=list(r.findings),
        citations=[_ser_citation(c) for c in r.citations],
        steps=[_ser_step(s) for s in r.steps],
        confidence_score=r.confidence_score,
        duration_ms=r.duration_ms,
        suggested_actions=list(r.suggested_actions),
        created_ts=r.created_ts,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/investigate-company",
    response_model=ResearchReportOut,
    summary="公司调研（DeepTutor 模式）",
)
async def investigate_company(
    payload: InvestigateCompanyIn,
    _user: User = Depends(get_current_user_required),
) -> ResearchReportOut:
    agent = get_market_agent()
    report = await agent.investigate_company(payload.company, depth=payload.depth)
    return _ser_report(report)


@router.post(
    "/competitor-monitor",
    response_model=CompetitorMonitorOut,
    summary="竞品监控（多家并行调研）",
)
async def competitor_monitor(
    payload: CompetitorMonitorIn,
    _user: User = Depends(get_current_user_required),
) -> CompetitorMonitorOut:
    agent = get_market_agent()
    results = await agent.monitor_competitors(
        payload.competitors, aspects=payload.aspects
    )
    items = {name: _ser_report(rep) for name, rep in results.items()}
    return CompetitorMonitorOut(items=items, total=len(items))


@router.post(
    "/industry-trends",
    response_model=IndustryTrendsOut,
    summary="行业趋势分析（4 维度切片）",
)
async def industry_trends(
    payload: IndustryTrendsIn,
    _user: User = Depends(get_current_user_required),
) -> IndustryTrendsOut:
    agent = get_market_agent()
    bundle = await agent.industry_trend_analysis(
        payload.industry, lookback_days=payload.lookback_days
    )
    axes_serialized = {
        k: [CitationOut(**c) for c in v] for k, v in (bundle.get("axes") or {}).items()
    }
    return IndustryTrendsOut(
        industry=bundle["industry"],
        lookback_days=bundle["lookback_days"],
        report=_ser_report(bundle["report"]),
        axes=axes_serialized,
    )


@router.post(
    "/deep-research",
    response_model=ResearchReportOut,
    summary="通用 DeepResearch（自定义问题）",
)
async def deep_research(
    payload: DeepResearchIn,
    _user: User = Depends(get_current_user_required),
) -> ResearchReportOut:
    agent = get_market_agent()
    report = await agent.deep_research(
        question=payload.question,
        max_iterations=payload.max_iterations,
        seed_queries=payload.seed_queries,
    )
    return _ser_report(report)


@router.get(
    "/research/{report_id}",
    response_model=ResearchReportOut,
    summary="读取此前生成的调研报告",
)
async def get_research(
    report_id: str,
    _user: User = Depends(get_current_user_required),
) -> ResearchReportOut:
    agent = get_market_agent()
    report = agent.get_report(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报告不存在或已被淘汰: {report_id}",
        )
    return _ser_report(report)

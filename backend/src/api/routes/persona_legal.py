# -*- coding: utf-8 -*-
"""法律顾问（legal_advisor）persona 路由 —— P9-B。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/legal"`` 注册）::

    POST   /api/v1/personas/legal/consult              body: { question, context? }
    POST   /api/v1/personas/legal/research             body: { keyword, law_type?, ... }
    POST   /api/v1/personas/legal/assess-risk          body: { scenario, jurisdiction? }
    POST   /api/v1/personas/legal/check-compliance     body: { document_text, regulation_set }
    GET    /api/v1/personas/legal/regulatory-updates   query: domain, since_days
    GET    /api/v1/personas/legal/legal-basis-explain  query: law_id

设计说明：
    - **agent 单例**：进程内共用一个 ``LegalAdvisorPersona``，包装 5 个
      specialized agent；测试可通过 ``set_agent_for_test()`` 替换
    - **不持久化**：报告 / 咨询结果不入库（V3 阶段先做无状态接口，
      会话历史走 chat 路由，本路由仅服务于结构化能力）
    - **鉴权**：复用全局 ``get_current_user_required``
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.agents.personas.legal_advisor import LegalAdvisorPersona
from src.agents.personas.legal_models import (
    Citation,
    ComplianceIssue,
    ComplianceReport,
    ConsultationResult,
    LawSearchQuery,
    RegulatoryUpdate,
    ResearchResult,
    RiskFactor,
    RiskReport,
)
from src.api.routes.schemas.persona_legal import (
    AssessRiskIn,
    CheckComplianceIn,
    CitationOut,
    ComplianceIssueOut,
    ComplianceReportOut,
    ConsultIn,
    ConsultationResultOut,
    LawSearchQueryOut,
    LegalBasisExplainOut,
    RegulatoryUpdateOut,
    RegulatoryUpdatesOut,
    ResearchIn,
    ResearchResultOut,
    RiskFactorOut,
    RiskReportOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# 单例 + 测试钩子
# ---------------------------------------------------------------------------

_agent: LegalAdvisorPersona | None = None


def get_legal_agent() -> LegalAdvisorPersona:
    """获取（懒构造）全局 ``LegalAdvisorPersona``。"""
    global _agent
    if _agent is None:
        _agent = LegalAdvisorPersona()
    return _agent


def set_agent_for_test(agent: LegalAdvisorPersona | None) -> None:
    """单测专用：替换 / 重置全局 agent。"""
    global _agent
    _agent = agent


# ---------------------------------------------------------------------------
# 序列化辅助（dataclass → Pydantic）
# ---------------------------------------------------------------------------


def _ser_citation(c: Citation) -> CitationOut:
    return CitationOut(
        source=c.source,
        article=c.article,
        url=c.url,
        title=c.title,
        excerpt=c.excerpt,
        effective_date=c.effective_date,
        confidence=float(c.confidence),
    )


def _ser_risk_factor(f: RiskFactor) -> RiskFactorOut:
    return RiskFactorOut(
        factor=f.factor,
        severity=f.severity,
        likelihood=f.likelihood,
        description=f.description,
    )


def _ser_compliance_issue(i: ComplianceIssue) -> ComplianceIssueOut:
    return ComplianceIssueOut(
        clause=i.clause,
        regulation=i.regulation,
        severity=i.severity,
        suggestion=i.suggestion,
    )


def _ser_consultation(r: ConsultationResult) -> ConsultationResultOut:
    return ConsultationResultOut(
        consultation_id=r.consultation_id,
        persona_id=r.persona_id,
        question=r.question,
        answer=r.answer,
        confidence=float(r.confidence),
        legal_basis=[_ser_citation(c) for c in r.legal_basis],
        related_topics=list(r.related_topics),
        suggested_actions=list(r.suggested_actions),
        disclaimer=r.disclaimer,
        created_ts=float(r.created_ts),
    )


def _ser_research(r: ResearchResult) -> ResearchResultOut:
    return ResearchResultOut(
        research_id=r.research_id,
        persona_id=r.persona_id,
        query=LawSearchQueryOut(
            keyword=r.query.keyword,
            law_type=r.query.law_type,
            jurisdiction=r.query.jurisdiction,
            effective_after=r.query.effective_after,
            limit=int(r.query.limit),
        ),
        summary=r.summary,
        citations=[_ser_citation(c) for c in r.citations],
        total_found=int(r.total_found),
        created_ts=float(r.created_ts),
    )


def _ser_risk_report(r: RiskReport) -> RiskReportOut:
    return RiskReportOut(
        report_id=r.report_id,
        persona_id=r.persona_id,
        scenario=r.scenario,
        risk_level=r.risk_level,
        risk_factors=[_ser_risk_factor(f) for f in r.risk_factors],
        mitigation_suggestions=list(r.mitigation_suggestions),
        regulatory_basis=[_ser_citation(c) for c in r.regulatory_basis],
        jurisdiction=r.jurisdiction,
        created_ts=float(r.created_ts),
    )


def _ser_compliance_report(r: ComplianceReport) -> ComplianceReportOut:
    return ComplianceReportOut(
        report_id=r.report_id,
        persona_id=r.persona_id,
        document_summary=r.document_summary,
        regulation_set=r.regulation_set,
        overall_compliance=r.overall_compliance,
        issues=[_ser_compliance_issue(i) for i in r.issues],
        score=float(r.score),
        created_ts=float(r.created_ts),
    )


def _ser_update(u: RegulatoryUpdate) -> RegulatoryUpdateOut:
    return RegulatoryUpdateOut(
        update_id=u.update_id,
        title=u.title,
        issuing_authority=u.issuing_authority,
        issued_date=u.issued_date,
        effective_date=u.effective_date,
        summary=u.summary,
        impact_assessment=u.impact_assessment,
        affected_domains=list(u.affected_domains),
        full_text_url=u.full_text_url,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/consult",
    response_model=ConsultationResultOut,
    summary="法律咨询（带免责声明 + 法条引用）",
)
async def consult(
    payload: ConsultIn,
    _user: User = Depends(get_current_user_required),
) -> ConsultationResultOut:
    agent = get_legal_agent()
    result = await agent.consult(payload.question, payload.context)
    return _ser_consultation(result)


@router.post(
    "/research",
    response_model=ResearchResultOut,
    summary="法规检索（关键词 → 法条 + 案例）",
)
async def research(
    payload: ResearchIn,
    _user: User = Depends(get_current_user_required),
) -> ResearchResultOut:
    agent = get_legal_agent()
    query = LawSearchQuery(
        keyword=payload.keyword,
        law_type=payload.law_type,
        jurisdiction=payload.jurisdiction,
        effective_after=payload.effective_after,
        limit=payload.limit,
    )
    result = await agent.research_law(query)
    return _ser_research(result)


@router.post(
    "/assess-risk",
    response_model=RiskReportOut,
    summary="法律风险评估（场景 → 风险等级 + 缓解建议）",
)
async def assess_risk(
    payload: AssessRiskIn,
    _user: User = Depends(get_current_user_required),
) -> RiskReportOut:
    agent = get_legal_agent()
    report = await agent.assess_risk(payload.scenario, payload.jurisdiction)
    return _ser_risk_report(report)


@router.post(
    "/check-compliance",
    response_model=ComplianceReportOut,
    summary="合规审查（文档 → 违规条款 + 评分）",
)
async def check_compliance(
    payload: CheckComplianceIn,
    _user: User = Depends(get_current_user_required),
) -> ComplianceReportOut:
    agent = get_legal_agent()
    report = await agent.review_compliance(payload.document_text, payload.regulation_set)
    return _ser_compliance_report(report)


@router.get(
    "/regulatory-updates",
    response_model=RegulatoryUpdatesOut,
    summary="法规更新监控（按领域 + 时间窗口）",
)
async def regulatory_updates(
    domain: str = Query(..., min_length=1, max_length=100, description="法律领域，如 '劳动法' / '数据合规'"),
    since_days: int = Query(30, ge=1, le=365, description="向前回溯天数"),
    _user: User = Depends(get_current_user_required),
) -> RegulatoryUpdatesOut:
    agent = get_legal_agent()
    updates = await agent.get_regulatory_updates(domain, since_days=since_days)
    return RegulatoryUpdatesOut(
        domain=domain,
        since_days=since_days,
        updates=[_ser_update(u) for u in updates],
        total=len(updates),
    )


@router.get(
    "/legal-basis-explain",
    response_model=LegalBasisExplainOut,
    summary="法条解释（输入法条 ID → 通俗解释 + 相关引用）",
)
async def legal_basis_explain(
    law_id: str = Query(..., min_length=1, max_length=200, description="法条标识，如 '劳动合同法#46'"),
    _user: User = Depends(get_current_user_required),
) -> LegalBasisExplainOut:
    """法条解释 —— 复用 ``consult()`` 通道（用「请解释 X」作为问题）。

    P9-B 阶段先以咨询模式落地，后续 P9-B.1 接入正式法条 KB 后切换到结构化检索。
    """
    if not law_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="law_id 不能为空",
        )
    agent = get_legal_agent()
    question = f"请用通俗易懂的语言解释 {law_id}，并列出相关条款的引用。"
    result = await agent.consult(question)
    # 尝试解析 law_id（"劳动合同法#46" → title=劳动合同法 / article=第46条）
    title = ""
    article = ""
    if "#" in law_id:
        parts = law_id.split("#", 1)
        title = parts[0].strip()
        if parts[1].strip():
            article = f"第{parts[1].strip()}条"
    else:
        title = law_id.strip()
    return LegalBasisExplainOut(
        law_id=law_id,
        title=title,
        article=article,
        explanation=result.answer,
        related_citations=[_ser_citation(c) for c in result.legal_basis],
    )

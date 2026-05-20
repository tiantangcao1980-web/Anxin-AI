"""persona_dd 路由 — P9-D 尽调专家 persona 对外 API。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/dd"`` 注册）::

    POST   /api/v1/personas/dd/investigate-company    body: { company_name, depth? }
    POST   /api/v1/personas/dd/analyze-evidence       body: { document_text, claim }
    POST   /api/v1/personas/dd/monitor-sentiment      body: { target, sources, lookback_days? }
    POST   /api/v1/personas/dd/relationship-graph     body: { entity, depth? }
    POST   /api/v1/personas/dd/grade-risk             body: { report_id? | dd_report? }
    GET    /api/v1/personas/dd/reports                query: target, generated_after
    GET    /api/v1/personas/dd/reports/{report_id}    缓存里读取已生成报告

设计说明：
    - **agent 单例**：进程内共用一个 ``DueDiligenceExpertPersona``；测试可
      通过 ``set_agent_for_test()`` 替换为带 mock 数据源的实例
    - **不持久化**：报告在 agent LRU 缓存（容量 100）；正式持久化由后续阶段补
    - **鉴权**：复用全局 ``get_current_user_required``
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.agents.personas.dd_models import (
    CompanyBasicInfo,
    CreditFlag,
    DueDiligenceReport,
    LitigationRecord,
)
from src.agents.personas.due_diligence_expert import DueDiligenceExpertPersona
from src.agents.personas.research_models import Citation
from src.api.routes.schemas.persona_dd import (
    AnalyzeEvidenceIn,
    CitationOut,
    CompanyBasicInfoOut,
    CreditFlagOut,
    DueDiligenceReportOut,
    EvidenceAnalysisOut,
    GradeRiskIn,
    InvestigateCompanyIn,
    ListReportsOut,
    LitigationRecordOut,
    MonitorSentimentIn,
    RelationshipEdgeOut,
    RelationshipGraphIn,
    RelationshipGraphOut,
    RelationshipNodeOut,
    RiskGradeOut,
    SentimentReportOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# 单例 + 测试钩子
# ---------------------------------------------------------------------------


_agent: DueDiligenceExpertPersona | None = None


def get_dd_agent() -> DueDiligenceExpertPersona:
    """获取（懒构造）全局尽调专家 agent。"""
    global _agent
    if _agent is None:
        _agent = DueDiligenceExpertPersona()
    return _agent


def set_agent_for_test(agent: DueDiligenceExpertPersona | None) -> None:
    """单测专用：替换 / 重置全局 agent。"""
    global _agent
    _agent = agent


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------


def _citation_out(c: Citation) -> CitationOut:
    return CitationOut(
        source=c.source,
        url=c.url,
        title=c.title,
        excerpt=c.excerpt,
        confidence=c.confidence,
    )


def _basic_info_out(b: CompanyBasicInfo | None) -> CompanyBasicInfoOut | None:
    if b is None:
        return None
    return CompanyBasicInfoOut(
        name=b.name,
        legal_representative=b.legal_representative,
        registered_capital=b.registered_capital,
        establishment_date=b.establishment_date,
        business_scope=b.business_scope,
        industry=b.industry,
        address=b.address,
        unified_credit_code=b.unified_credit_code,
        status=b.status,
    )


def _litigation_out(r: LitigationRecord) -> LitigationRecordOut:
    return LitigationRecordOut(
        case_number=r.case_number,
        case_type=r.case_type,
        court=r.court,
        role=r.role,
        amount_disputed=r.amount_disputed,
        judgment_date=r.judgment_date,
        judgment_summary=r.judgment_summary,
        full_text_url=r.full_text_url,
    )


def _credit_flag_out(f: CreditFlag) -> CreditFlagOut:
    return CreditFlagOut(
        flag_type=f.flag_type,
        description=f.description,
        issued_date=f.issued_date,
        issuing_authority=f.issuing_authority,
        severity=f.severity,
    )


def _report_out(rep: DueDiligenceReport) -> DueDiligenceReportOut:
    return DueDiligenceReportOut(
        report_id=rep.report_id,
        target=rep.target,
        target_type=rep.target_type,
        investigation_depth=rep.investigation_depth,
        basic_info=_basic_info_out(rep.basic_info),
        shareholders=list(rep.shareholders),
        key_personnel=list(rep.key_personnel),
        litigation_records=[_litigation_out(r) for r in rep.litigation_records],
        credit_flags=[_credit_flag_out(f) for f in rep.credit_flags],
        intellectual_properties=list(rep.intellectual_properties),
        public_news_count=rep.public_news_count,
        overall_risk_level=rep.overall_risk_level,
        summary=rep.summary,
        recommendations=list(rep.recommendations),
        generated_at=rep.generated_at,
        citations=[_citation_out(c) for c in rep.citations],
    )


def _report_in_to_dataclass(payload: DueDiligenceReportOut) -> DueDiligenceReport:
    """把 API 入参的 ``DueDiligenceReportOut`` 还原成内部 dataclass。"""
    basic = None
    if payload.basic_info is not None:
        bi = payload.basic_info
        basic = CompanyBasicInfo(
            name=bi.name,
            legal_representative=bi.legal_representative,
            registered_capital=bi.registered_capital,
            establishment_date=bi.establishment_date,
            business_scope=bi.business_scope,
            industry=bi.industry,
            address=bi.address,
            unified_credit_code=bi.unified_credit_code,
            status=bi.status,
        )
    return DueDiligenceReport(
        target=payload.target,
        target_type=payload.target_type,
        investigation_depth=payload.investigation_depth,
        basic_info=basic,
        shareholders=list(payload.shareholders),
        key_personnel=list(payload.key_personnel),
        litigation_records=[
            LitigationRecord(
                case_number=r.case_number,
                case_type=r.case_type,
                court=r.court,
                role=r.role,
                amount_disputed=r.amount_disputed,
                judgment_date=r.judgment_date,
                judgment_summary=r.judgment_summary,
                full_text_url=r.full_text_url,
            )
            for r in payload.litigation_records
        ],
        credit_flags=[
            CreditFlag(
                flag_type=f.flag_type,
                description=f.description,
                issued_date=f.issued_date,
                issuing_authority=f.issuing_authority,
                severity=f.severity,
            )
            for f in payload.credit_flags
        ],
        intellectual_properties=list(payload.intellectual_properties),
        public_news_count=payload.public_news_count,
        overall_risk_level=payload.overall_risk_level,
        summary=payload.summary,
        recommendations=list(payload.recommendations),
        generated_at=payload.generated_at,
        citations=[
            Citation(
                source=c.source,
                url=c.url,
                title=c.title,
                excerpt=c.excerpt,
                confidence=c.confidence,
            )
            for c in payload.citations
        ],
        report_id=payload.report_id,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/investigate-company", response_model=DueDiligenceReportOut)
async def investigate_company(
    payload: InvestigateCompanyIn,
    user: User = Depends(get_current_user_required),
) -> DueDiligenceReportOut:
    """对公司发起 quick / standard / deep 尽调。"""
    agent = get_dd_agent()
    report = await agent.investigate_company(
        company_name=payload.company_name,
        depth=payload.depth,
    )
    return _report_out(report)


@router.post("/analyze-evidence", response_model=EvidenceAnalysisOut)
async def analyze_evidence(
    payload: AnalyzeEvidenceIn,
    user: User = Depends(get_current_user_required),
) -> EvidenceAnalysisOut:
    """分析文档是否支持给定主张 + 真伪指标。"""
    agent = get_dd_agent()
    result = await agent.analyze_evidence(
        document_text=payload.document_text,
        claim=payload.claim,
    )
    return EvidenceAnalysisOut(
        document_summary=result.document_summary,
        claim=result.claim,
        supports_claim=result.supports_claim,
        confidence=result.confidence,
        supporting_excerpts=result.supporting_excerpts,
        contradicting_excerpts=result.contradicting_excerpts,
        inconsistencies=result.inconsistencies,
        authenticity_score=result.authenticity_score,
        forgery_indicators=result.forgery_indicators,
    )


@router.post("/monitor-sentiment", response_model=SentimentReportOut)
async def monitor_sentiment(
    payload: MonitorSentimentIn,
    user: User = Depends(get_current_user_required),
) -> SentimentReportOut:
    """聚合多源舆情。"""
    agent = get_dd_agent()
    result = await agent.monitor_sentiment(
        target=payload.target,
        sources=list(payload.sources),
        lookback_days=payload.lookback_days,
    )
    return SentimentReportOut(
        target=result.target,
        period_start=result.period_start,
        period_end=result.period_end,
        overall_sentiment=result.overall_sentiment,
        sentiment_score=result.sentiment_score,
        volume=result.volume,
        by_source=result.by_source,
        top_topics=result.top_topics,
        notable_events=result.notable_events,
        trend=result.trend,
    )


@router.post("/relationship-graph", response_model=RelationshipGraphOut)
async def relationship_graph(
    payload: RelationshipGraphIn,
    user: User = Depends(get_current_user_required),
) -> RelationshipGraphOut:
    """从 entity 出发做受限深度 BFS 关系图谱。"""
    agent = get_dd_agent()
    graph = await agent.build_relationship_graph(
        entity=payload.entity,
        depth=payload.depth,
    )
    return RelationshipGraphOut(
        root_entity=graph.root_entity,
        nodes=[
            RelationshipNodeOut(id=n.id, name=n.name, type=n.type, attributes=n.attributes)
            for n in graph.nodes
        ],
        edges=[
            RelationshipEdgeOut(
                from_id=e.from_id,
                to_id=e.to_id,
                relationship=e.relationship,
                confidence=e.confidence,
                source=e.source,
            )
            for e in graph.edges
        ],
        depth=graph.depth,
        risk_paths=graph.risk_paths,
    )


@router.post("/grade-risk", response_model=RiskGradeOut)
async def grade_risk(
    payload: GradeRiskIn,
    user: User = Depends(get_current_user_required),
) -> RiskGradeOut:
    """对已生成的尽调报告打 AAA-D 等级 + 推荐操作。"""
    agent = get_dd_agent()
    if payload.report_id:
        cached = agent.get_cached_report(payload.report_id)
        if cached is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail=f"report_id={payload.report_id} 不存在"
            )
        report = cached
    elif payload.dd_report is not None:
        report = _report_in_to_dataclass(payload.dd_report)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="必须提供 report_id 或 dd_report 之一",
        )

    grade = await agent.grade_risk(report)
    return RiskGradeOut(
        grade=grade.grade,
        score=grade.score,
        breakdown=grade.breakdown,
        rationale=grade.rationale,
        red_flags=grade.red_flags,
        recommended_action=grade.recommended_action,
    )


@router.get("/reports", response_model=ListReportsOut)
async def list_reports(
    user: User = Depends(get_current_user_required),
    target: str | None = Query(default=None),
    generated_after: datetime | None = Query(default=None),
) -> ListReportsOut:
    """列出当前进程缓存内的尽调报告。"""
    agent = get_dd_agent()
    reports = agent.list_cached_reports(target=target, generated_after=generated_after)
    return ListReportsOut(
        items=[_report_out(r) for r in reports],
        total=len(reports),
    )


@router.get("/reports/{report_id}", response_model=DueDiligenceReportOut)
async def get_report(
    report_id: str,
    user: User = Depends(get_current_user_required),
) -> DueDiligenceReportOut:
    """读取指定 report_id 的缓存报告。"""
    agent = get_dd_agent()
    rep = agent.get_cached_report(report_id)
    if rep is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"report_id={report_id} 不存在")
    return _report_out(rep)

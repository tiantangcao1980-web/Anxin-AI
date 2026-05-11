# -*- coding: utf-8 -*-
"""合同管家 persona 路由（P9-C）。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/contract"`` 注册）::

    POST   /api/v1/personas/contract/draft
    POST   /api/v1/personas/contract/review
    POST   /api/v1/personas/contract/identify-risks
    GET    /api/v1/personas/contract/templates
    POST   /api/v1/personas/contract/compare-versions
    POST   /api/v1/personas/contract/archive
    GET    /api/v1/personas/contract/archives

权限：所有路由都要求登录用户（与同期 persona 路由一致）。

存储说明（archives）：
    - 当前阶段把归档结果保存在进程内的 ``_ARCHIVE_STORE``（按 user_id 隔离）。
    - 后续接入 ``services.document_service`` 与 OSS 后再迁移；本阶段保持
      contract 不依赖任何新的 model / service，避免越界。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, DefaultDict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.agents.personas.contract_steward import ContractStewardPersona
from src.api.routes.schemas.persona_contract import (
    ArchiveIn,
    ArchiveListOut,
    ArchiveResultOut,
    CitationOut,
    CompareVersionsIn,
    ContractDraftOut,
    DraftContractIn,
    IdentifyRisksIn,
    ReviewContractIn,
    ReviewIssueOut,
    ReviewReportOut,
    RiskAnalysisOut,
    TemplateListOut,
    TemplateOut,
    VersionDiffOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Persona 单例 + 进程内归档存储（按 user_id 隔离，仅本期使用）
# ---------------------------------------------------------------------------
_PERSONA = ContractStewardPersona()
_ARCHIVE_STORE: DefaultDict[str, List[ArchiveResultOut]] = defaultdict(list)


def _get_persona() -> ContractStewardPersona:
    """依赖注入入口；测试可通过 ``app.dependency_overrides`` 替换。"""
    return _PERSONA


def _user_key(user: User) -> str:
    return str(getattr(user, "id", "anon") or "anon")


# ---------------------------------------------------------------------------
# 1. draft
# ---------------------------------------------------------------------------
@router.post(
    "/draft",
    response_model=ContractDraftOut,
    summary="起草合同（采购 / NDA / 服务 / 劳动 等）",
)
async def draft_contract(
    payload: DraftContractIn,
    persona: ContractStewardPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> ContractDraftOut:
    try:
        draft = await persona.draft_contract(
            contract_type=payload.contract_type,
            parties=[p.model_dump() for p in payload.parties],
            terms=payload.terms or {},
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ContractDraftOut(
        contract_type=draft.contract_type,
        title=draft.title,
        full_text=draft.full_text,
        sections=draft.sections,
        suggested_clauses=draft.suggested_clauses,
        estimated_word_count=draft.estimated_word_count,
        language=draft.language,
        docx_template_path=draft.docx_template_path,
    )


# ---------------------------------------------------------------------------
# 2. review
# ---------------------------------------------------------------------------
@router.post(
    "/review",
    response_model=ReviewReportOut,
    summary="审查合同（buyer / seller / neutral 三立场）",
)
async def review_contract(
    payload: ReviewContractIn,
    persona: ContractStewardPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> ReviewReportOut:
    try:
        report = await persona.review_contract(
            document_text=payload.document_text,
            perspective=payload.perspective,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ReviewReportOut(
        overall_assessment=report.overall_assessment,
        perspective=report.perspective,
        score=report.score,
        issues=[
            ReviewIssueOut(
                clause_text=i.clause_text,
                issue_type=i.issue_type,
                severity=i.severity,
                description=i.description,
                suggested_revision=i.suggested_revision,
                location=i.location,
            )
            for i in report.issues
        ],
        missing_clauses=report.missing_clauses,
        redundant_clauses=report.redundant_clauses,
        recommendation=report.recommendation,
    )


# ---------------------------------------------------------------------------
# 3. identify-risks
# ---------------------------------------------------------------------------
@router.post(
    "/identify-risks",
    response_model=RiskAnalysisOut,
    summary="风险识别（中立立场，给评级 + 法条 + 缓解措施）",
)
async def identify_risks(
    payload: IdentifyRisksIn,
    persona: ContractStewardPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> RiskAnalysisOut:
    try:
        analysis = await persona.identify_risks(payload.document_text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RiskAnalysisOut(
        overall_risk_level=analysis.overall_risk_level,
        risks=analysis.risks,
        blacklist_clauses=analysis.blacklist_clauses,
        legal_basis=[
            CitationOut(
                source=c.source,
                url=c.url,
                title=c.title,
                excerpt=c.excerpt,
                confidence=c.confidence,
            )
            for c in analysis.legal_basis
        ],
    )


# ---------------------------------------------------------------------------
# 4. templates
# ---------------------------------------------------------------------------
@router.get(
    "/templates",
    response_model=TemplateListOut,
    summary="模板库检索（关键词 + 可选合同类型过滤）",
)
async def find_templates(
    q: str = Query(..., min_length=1, max_length=200, description="检索关键词"),
    contract_type: str | None = Query(None, max_length=100),
    persona: ContractStewardPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> TemplateListOut:
    try:
        items = await persona.find_template(query=q, contract_type=contract_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    out = [
        TemplateOut(
            template_id=t.template_id,
            name=t.name,
            contract_type=t.contract_type,
            description=t.description,
            use_case=t.use_case,
            language=t.language,
            word_count=t.word_count,
            last_used=t.last_used.isoformat() if t.last_used else None,
            download_url=t.download_url,
        )
        for t in items
    ]
    return TemplateListOut(items=out, total=len(out))


# ---------------------------------------------------------------------------
# 5. compare-versions
# ---------------------------------------------------------------------------
@router.post(
    "/compare-versions",
    response_model=VersionDiffOut,
    summary="版本对比（结构 + 语义级 diff）",
)
async def compare_versions(
    payload: CompareVersionsIn,
    persona: ContractStewardPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> VersionDiffOut:
    try:
        diff = await persona.compare_versions(payload.v1_text, payload.v2_text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return VersionDiffOut(
        v1_summary=diff.v1_summary,
        v2_summary=diff.v2_summary,
        additions=diff.additions,
        deletions=diff.deletions,
        modifications=diff.modifications,
        semantic_changes=diff.semantic_changes,
    )


# ---------------------------------------------------------------------------
# 6. archive
# ---------------------------------------------------------------------------
@router.post(
    "/archive",
    response_model=ArchiveResultOut,
    summary="归档合同（写入元数据 + 默认保留期）",
)
async def archive_contract(
    payload: ArchiveIn,
    persona: ContractStewardPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),
) -> ArchiveResultOut:
    try:
        res = await persona.archive(
            contract_id=payload.contract_id,
            metadata=payload.metadata,
            retention_period_days=payload.retention_period_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    out = ArchiveResultOut(
        contract_id=res.contract_id,
        archive_url=res.archive_url,
        metadata=res.metadata,
        archived_at=res.archived_at.isoformat(),
        retention_period_days=res.retention_period_days,
    )
    _ARCHIVE_STORE[_user_key(user)].append(out)
    return out


# ---------------------------------------------------------------------------
# 7. archives list
# ---------------------------------------------------------------------------
@router.get(
    "/archives",
    response_model=ArchiveListOut,
    summary="归档列表（支持按当事方 / 时间区间过滤）",
)
async def list_archives(
    party: str | None = Query(None, max_length=200),
    date_from: str | None = Query(None, description="ISO 8601 日期（含）"),
    date_to: str | None = Query(None, description="ISO 8601 日期（含）"),
    user: User = Depends(get_current_user_required),
) -> ArchiveListOut:
    items = list(_ARCHIVE_STORE.get(_user_key(user), []))

    def _within(it: ArchiveResultOut) -> bool:
        if party:
            md = it.metadata or {}
            parties = md.get("parties") or []
            joined = " ".join(str(p) for p in parties) + " " + str(md.get("party", ""))
            if party.lower() not in joined.lower():
                return False
        if date_from or date_to:
            try:
                ts = datetime.fromisoformat(it.archived_at)
            except Exception:
                return True
            if date_from:
                try:
                    if ts < datetime.fromisoformat(date_from):
                        return False
                except Exception:
                    pass
            if date_to:
                try:
                    if ts > datetime.fromisoformat(date_to):
                        return False
                except Exception:
                    pass
        return True

    filtered = [it for it in items if _within(it)]
    return ArchiveListOut(items=filtered, total=len(filtered))


__all__ = ["router"]

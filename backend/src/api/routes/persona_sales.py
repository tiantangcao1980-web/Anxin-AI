"""persona_sales 路由 — P7-C 获客猎手 persona 对外 API。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/sales"`` 注册）::

    POST   /api/v1/personas/sales/discover-leads
    POST   /api/v1/personas/sales/draft-email
    POST   /api/v1/personas/sales/generate-quote          → 报价单 .docx URL
    POST   /api/v1/personas/sales/sync-crm
    POST   /api/v1/personas/sales/linkedin-outreach
    GET    /api/v1/personas/sales/leads                    query: status / score_min

权限：所有 endpoint 都要登录用户。
"""

from __future__ import annotations

import base64
import threading
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.agents.personas.lead_hunter import LeadHunterAgent
from src.agents.personas.sales_models import (
    Contact,
    Lead,
    LeadDiscoveryCriteria,
    QuoteItem,
    QuoteTerms,
)
from src.api.routes.schemas.persona_sales import (
    ContactOut,
    CrmSyncIn,
    CrmSyncOut,
    DiscoverLeadsIn,
    DiscoverLeadsOut,
    DraftEmailIn,
    EmailDraftOut,
    GenerateQuoteIn,
    GenerateQuoteOut,
    LeadCandidateIn,
    LeadOut,
    LinkedinOutreachIn,
    LinkedinOutreachOut,
    ListLeadsOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()

# ---------------------------------------------------------------------------
# 进程内 lead 缓存（仅 P7-C 阶段；正式持久化由 P7-E + Lead 表完成）
# ---------------------------------------------------------------------------

_LEAD_STORE: dict[str, dict[str, Lead]] = {}  # user_id -> {lead_id -> Lead}
_STORE_LOCK = threading.Lock()


def _put_leads(user_id: str, leads: list[Lead]) -> None:
    with _STORE_LOCK:
        bucket = _LEAD_STORE.setdefault(user_id, {})
        for lead in leads:
            bucket[lead.id] = lead


def _list_leads(user_id: str) -> list[Lead]:
    with _STORE_LOCK:
        return list(_LEAD_STORE.get(user_id, {}).values())


# ---------------------------------------------------------------------------
# 序列化 helpers
# ---------------------------------------------------------------------------


def _candidate_to_lead(payload: LeadCandidateIn) -> Lead:
    """LeadCandidateIn → Lead dataclass。用于 draft / quote / crm 入参。"""
    contacts = [
        Contact(
            name=c.name,
            title=c.title,
            email=c.email,
            linkedin_url=c.linkedin_url,
            phone=c.phone,
        )
        for c in payload.contacts
    ]
    return Lead(
        id=payload.id or f"lead-{payload.company_name[:6]}",
        company_name=payload.company_name,
        industry=payload.industry,
        country=payload.country,
        employees_estimate=payload.employees_estimate,
        revenue_estimate=payload.revenue_estimate,
        contacts=contacts,
        tags=list(payload.tags),
        source=payload.source,
    )


def _lead_to_out(lead: Lead) -> LeadOut:
    return LeadOut(
        id=lead.id,
        company_name=lead.company_name,
        industry=lead.industry,
        country=lead.country,
        employees_estimate=lead.employees_estimate,
        revenue_estimate=lead.revenue_estimate,
        contacts=[
            ContactOut(
                name=c.name,
                title=c.title,
                email=c.email,
                linkedin_url=c.linkedin_url,
                phone=c.phone,
                is_decision_maker=c.is_decision_maker(),
            )
            for c in lead.contacts
        ],
        score=lead.score,
        tags=lead.tags,
        source=lead.source,
        discovered_at=lead.discovered_at,
        score_breakdown=lead.score_breakdown,
    )


def _agent() -> LeadHunterAgent:
    return LeadHunterAgent()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/discover-leads", response_model=DiscoverLeadsOut)
async def discover_leads(
    payload: DiscoverLeadsIn,
    user: User = Depends(get_current_user_required),
) -> DiscoverLeadsOut:
    """根据 criteria + candidates 返回评分排序后的 leads。"""
    criteria = LeadDiscoveryCriteria(
        industry=payload.industry,
        region=payload.region,
        company_size=payload.company_size,
        keywords=list(payload.keywords),
        exclude_competitors=payload.exclude_competitors,
        limit=payload.limit,
    )
    candidates_raw: list[dict[str, Any]] = [c.model_dump() for c in payload.candidates]
    leads = await _agent().discover_leads(criteria, candidates=candidates_raw)
    _put_leads(str(user.id), leads)
    return DiscoverLeadsOut(items=[_lead_to_out(lead) for lead in leads], total=len(leads))


@router.post("/draft-email", response_model=EmailDraftOut)
async def draft_email(
    payload: DraftEmailIn,
    user: User = Depends(get_current_user_required),
) -> EmailDraftOut:
    """给定一个 lead，起草指定 intent / 语言的销售邮件。"""
    lead = _candidate_to_lead(payload.lead)
    draft = await _agent().draft_email(
        lead,
        intent=payload.intent,
        language=payload.language,
        sender=payload.sender or {},
        hooks=payload.hooks or {},
    )
    return EmailDraftOut(
        subject=draft.subject,
        body=draft.body,
        language=draft.language,
        cta=draft.cta,
        estimated_response_rate=draft.estimated_response_rate,
        subject_variants=draft.subject_variants,
        template_id=draft.template_id,
    )


@router.post("/generate-quote", response_model=GenerateQuoteOut)
async def generate_quote(
    payload: GenerateQuoteIn,
    user: User = Depends(get_current_user_required),
) -> GenerateQuoteOut:
    """生成报价单 .docx，目前以 base64 data URL 形式返回 file_url。

    P7-D 接入对象存储后会替换成 https URL。
    """
    if not payload.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="items 不能为空")

    lead = _candidate_to_lead(payload.lead)
    items = [
        QuoteItem(
            sku=it.sku,
            name=it.name,
            description=it.description,
            quantity=it.quantity,
            unit_price=it.unit_price,
            currency=it.currency,
            discount_pct=it.discount_pct,
        )
        for it in payload.items
    ]
    terms = QuoteTerms(
        payment_terms=payload.terms.payment_terms,
        delivery_terms=payload.terms.delivery_terms,
        lead_time_days=payload.terms.lead_time_days,
        validity_days=payload.terms.validity_days,
        warranty=payload.terms.warranty,
        notes=payload.terms.notes,
    )

    docx_bytes = await _agent().generate_quote(lead, items, terms)
    subtotal = round(sum(it.line_total for it in items), 2)
    currency = items[0].currency
    file_url = "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64," + base64.b64encode(
        docx_bytes
    ).decode("ascii")
    return GenerateQuoteOut(
        file_url=file_url,
        bytes_size=len(docx_bytes),
        subtotal=subtotal,
        currency=currency,
        items_count=len(items),
    )


@router.post("/sync-crm", response_model=CrmSyncOut)
async def sync_crm(
    payload: CrmSyncIn,
    user: User = Depends(get_current_user_required),
) -> CrmSyncOut:
    leads = [_candidate_to_lead(c) for c in payload.leads]
    result = await _agent().sync_to_crm(
        leads, crm=payload.crm, oauth_token=payload.oauth_token
    )
    return CrmSyncOut(**result)


@router.post("/linkedin-outreach", response_model=LinkedinOutreachOut)
async def linkedin_outreach(
    payload: LinkedinOutreachIn,
    user: User = Depends(get_current_user_required),
) -> LinkedinOutreachOut:
    result = await _agent().linkedin_outreach(
        profile_url=payload.profile_url,
        message_template=payload.message_template,
        oauth_token=payload.oauth_token,
    )
    return LinkedinOutreachOut(**result)


@router.get("/leads", response_model=ListLeadsOut)
async def list_leads(
    user: User = Depends(get_current_user_required),
    status_filter: str | None = Query(default=None, alias="status"),
    score_min: float = Query(default=0.0, ge=0.0, le=1.0),
) -> ListLeadsOut:
    """列出当前用户已 discover 过的 leads。

    - ``status`` query：仅按 tag 简单过滤（"hot" / "warm" / "cold"）。
    - ``score_min``：score >= score_min。
    """
    leads = _list_leads(str(user.id))
    filtered: list[Lead] = []
    for lead in leads:
        if lead.score < score_min:
            continue
        if status_filter:
            sf = status_filter.lower()
            tagged = sf in [t.lower() for t in lead.tags]
            inferred = (
                (sf == "hot" and lead.score >= 0.7)
                or (sf == "warm" and 0.4 <= lead.score < 0.7)
                or (sf == "cold" and lead.score < 0.4)
            )
            if not tagged and not inferred:
                continue
        filtered.append(lead)
    filtered.sort(key=lambda lead: lead.score, reverse=True)
    return ListLeadsOut(items=[_lead_to_out(lead) for lead in filtered], total=len(filtered))

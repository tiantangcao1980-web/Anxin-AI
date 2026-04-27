# -*- coding: utf-8 -*-
"""persona_sales 路由 Pydantic schemas（请求 / 响应 DTO）。

P7-C 获客猎手 persona 对外 API 的 IO 类型。所有字段 camelCase 与 snake_case
都允许（``populate_by_name=True``），方便前后端 contract。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Lead Discovery
# ---------------------------------------------------------------------------


class ContactIn(BaseModel):
    name: str
    title: str
    email: str | None = None
    linkedin_url: str | None = None
    phone: str | None = None


class ContactOut(BaseModel):
    name: str
    title: str
    email: str | None = None
    linkedin_url: str | None = None
    phone: str | None = None
    is_decision_maker: bool = False


class LeadCandidateIn(BaseModel):
    """前端 / 上游数据源送进来的原始候选 lead。"""

    company_name: str
    industry: str = ""
    country: str = ""
    employees_estimate: int | None = None
    revenue_estimate: float | None = None
    contacts: list[ContactIn] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"
    signals: dict[str, float] = Field(default_factory=dict)
    id: str | None = None


class DiscoverLeadsIn(BaseModel):
    industry: str
    region: str | None = None
    company_size: str | None = None
    keywords: list[str] = Field(default_factory=list)
    exclude_competitors: bool = True
    limit: int = Field(default=50, ge=1, le=500)
    candidates: list[LeadCandidateIn] = Field(default_factory=list)


class LeadOut(BaseModel):
    id: str
    company_name: str
    industry: str
    country: str
    employees_estimate: int | None = None
    revenue_estimate: float | None = None
    contacts: list[ContactOut] = Field(default_factory=list)
    score: float
    tags: list[str] = Field(default_factory=list)
    source: str
    discovered_at: datetime
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class DiscoverLeadsOut(BaseModel):
    items: list[LeadOut]
    total: int


# ---------------------------------------------------------------------------
# Email Drafting
# ---------------------------------------------------------------------------


class DraftEmailIn(BaseModel):
    lead: LeadCandidateIn
    intent: Literal["cold_intro", "follow_up", "proposal"] = "cold_intro"
    language: Literal["zh", "en", "ja"] = "zh"
    sender: dict[str, str] = Field(default_factory=dict)
    hooks: dict[str, str] = Field(default_factory=dict)


class EmailDraftOut(BaseModel):
    subject: str
    body: str
    language: str
    cta: str
    estimated_response_rate: float
    subject_variants: list[str] = Field(default_factory=list)
    template_id: str | None = None


# ---------------------------------------------------------------------------
# Quote Generation
# ---------------------------------------------------------------------------


class QuoteItemIn(BaseModel):
    sku: str
    name: str
    description: str | None = None
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    currency: str = "USD"
    discount_pct: float = Field(default=0.0, ge=0, le=100)


class QuoteTermsIn(BaseModel):
    payment_terms: str = "T/T 30% deposit, 70% before shipment"
    delivery_terms: str = "FOB Shenzhen"
    lead_time_days: int = 30
    validity_days: int = 30
    warranty: str = "12 months"
    notes: str | None = None


class GenerateQuoteIn(BaseModel):
    lead: LeadCandidateIn
    items: list[QuoteItemIn]
    terms: QuoteTermsIn = Field(default_factory=QuoteTermsIn)


class GenerateQuoteOut(BaseModel):
    file_url: str
    bytes_size: int
    subtotal: float
    currency: str
    items_count: int


# ---------------------------------------------------------------------------
# CRM Sync
# ---------------------------------------------------------------------------


class CrmSyncIn(BaseModel):
    leads: list[LeadCandidateIn]
    crm: Literal["salesforce", "hubspot", "pipedrive", "zoho"]
    oauth_token: str = Field(min_length=1)


class CrmSyncOut(BaseModel):
    crm: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# LinkedIn Outreach
# ---------------------------------------------------------------------------


class LinkedinOutreachIn(BaseModel):
    profile_url: str
    message_template: str = Field(max_length=300)
    oauth_token: str = Field(min_length=1)


class LinkedinOutreachOut(BaseModel):
    ok: bool
    status: str | None = None
    error: str | None = None
    detail: str | None = None
    profile_url: str | None = None
    message_preview: str | None = None
    note: str | None = None


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


class ListLeadsOut(BaseModel):
    items: list[LeadOut]
    total: int

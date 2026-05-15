"""获客猎手 (lead_hunter) Persona 的数据模型。

仅 dataclass，不依赖任何 ORM / FastAPI / 持久层。后端 service 会把这些
对象序列化进 Pydantic schema。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Lead 发掘
# ---------------------------------------------------------------------------


@dataclass
class LeadDiscoveryCriteria:
    """前端 / 上游 agent 提交的潜客发掘条件。"""

    industry: str
    region: str | None = None  # "广东省" / "Southeast Asia" / "DE"
    company_size: str | None = None  # "50-500" / "500+" / "<50"
    keywords: list[str] = field(default_factory=list)
    exclude_competitors: bool = True
    limit: int = 50

    def normalized_keywords(self) -> list[str]:
        return [k.strip().lower() for k in self.keywords if k and k.strip()]


# ---------------------------------------------------------------------------
# Contact / Lead
# ---------------------------------------------------------------------------


@dataclass
class Contact:
    """潜客的关键联系人。

    title 用于判断是否决策人（VP/Director/CXO/Founder/采购总监 等）。
    """

    name: str
    title: str
    email: str | None = None
    linkedin_url: str | None = None
    phone: str | None = None

    def is_decision_maker(self) -> bool:
        title = (self.title or "").lower()
        decision_keywords = [
            "ceo",
            "cto",
            "cfo",
            "cmo",
            "founder",
            "co-founder",
            "owner",
            "president",
            "vp",
            "vice president",
            "director",
            "head of",
            "总裁",
            "总经理",
            "总监",
            "创始人",
            "采购总监",
            "采购经理",
            "副总",
        ]
        return any(k in title for k in decision_keywords)


@dataclass
class Lead:
    """B2B 潜在客户记录。score 0-1，越高越 hot。"""

    id: str
    company_name: str
    industry: str
    country: str
    employees_estimate: int | None = None
    revenue_estimate: float | None = None  # USD
    contacts: list[Contact] = field(default_factory=list)
    score: float = 0.0
    tags: list[str] = field(default_factory=list)
    source: str = "manual"  # "linkedin" / "qichacha" / "manual"
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    # 评分辅助字段（由 LeadScoring 写回，便于审计）
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def has_decision_maker(self) -> bool:
        return any(c.is_decision_maker() for c in self.contacts)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


@dataclass
class EmailDraft:
    """销售邮件草稿。subject 可附加 AB 变体放在 ``subject_variants``。"""

    subject: str
    body: str
    language: str  # "zh" / "en" / "ja"
    cta: str
    estimated_response_rate: float = 0.0  # 0-1
    subject_variants: list[str] = field(default_factory=list)
    template_id: str | None = None  # cold_intro_zh / follow_up_en / proposal_jp ...


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------


@dataclass
class QuoteItem:
    sku: str
    name: str
    description: str | None
    quantity: int
    unit_price: float
    currency: str
    discount_pct: float = 0.0

    @property
    def line_total(self) -> float:
        gross = self.unit_price * self.quantity
        return round(gross * (1 - self.discount_pct / 100.0), 2)


@dataclass
class QuoteTerms:
    """报价单条款。FastAPI 路由层用 dict 透传，agent 内部转此 dataclass。"""

    payment_terms: str = "T/T 30% deposit, 70% before shipment"
    delivery_terms: str = "FOB Shenzhen"
    lead_time_days: int = 30
    validity_days: int = 30
    warranty: str = "12 months"
    notes: str | None = None


# ---------------------------------------------------------------------------
# CRM 同步结果
# ---------------------------------------------------------------------------


@dataclass
class CrmSyncResult:
    crm: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

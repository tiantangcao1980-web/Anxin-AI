# -*- coding: utf-8 -*-
"""跨境电商助手 — 数据模型（P7-E）。

本模块定义了 ``EcommerceAssistantAgent`` 在 6 大能力（选品 / 验商 / 议价 /
建站 / 铺货 / VAT）上往外吐的强类型结构。

设计取舍
--------
- **dataclass 而非 pydantic**：persona 是 agent 内部能力契约，与 Web SDK
  schema (``api/routes/schemas/persona_ecommerce.py``) 解耦 —— 让 API 层
  保持 pydantic、agent 层保持轻量。
- **金额 / 比率统一 float**：跨境业务货币、利率精度 ≤4 位即可，避免
  decimal 在 LLM JSON 序列化里出 "Object not JSON serializable"。
- **citations / disclaimer 是一等公民**：选品和 VAT 都涉及外部数据，必须
  追溯来源 + 法律免责声明，避免误导用户做高风险决策。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NicheReport:
    """单个细分赛道（niche）的市场调研报告。

    - ``competition_level``: ``"low"`` / ``"medium"`` / ``"high"`` —
      red ocean 程度的归一表达，由 LLM 综合 BSR / 评论数 / Top10 利润率
      给出。
    - ``avg_price_band``: ``(min, max)`` 美元价格带；前端绘制时直接做条形图。
    - ``recommended_action``: ``"enter"`` / ``"wait"`` / ``"skip"`` —
      可被路由层映射到下一步动作（启动选品 / 加入观察列表 / 归档）。
    - ``citations``: 数据来源列表，每项形如
      ``{"source": "amazon_sp", "url": "...", "snippet": "..."}``。
    """

    niche: str
    market_size_usd: float
    growth_rate_pct: float
    competition_level: str
    avg_price_band: tuple[float, float]
    profit_margin_estimate_pct: float
    top_competitors: list[dict]
    seasonal_pattern: str
    recommended_action: str
    rationale: str
    citations: list[dict] = field(default_factory=list)


@dataclass
class SupplierVerification:
    """供应商验真结果（主要面向 1688 / 阿里巴巴国际站厂家）。

    - ``factory_audit_grade``: ``"A"`` / ``"B"`` / ``"C"`` / ``None`` —
      平台官方验厂结果；``None`` 表示无审核数据。
    - ``moq``: 最小起订量，单位 = 件；下游议价模块据此评估首单成本。
    - ``capacity_per_month``: 月产能（件/月），缺失时为 ``None``。
    - ``customs_records_count``: 海关公开记录次数 — 出口次数越多通常越稳。
    - ``risk_flags``: 已识别的风险关键词列表（如 ``"trademark_dispute"``、
      ``"frequent_name_change"``）。
    - ``recommendation``: ``"trust"`` / ``"verify_more"`` / ``"avoid"``。
    """

    supplier_id: str
    name: str
    business_license_verified: bool
    factory_audit_grade: str | None
    years_in_business: int | None
    moq: int
    capacity_per_month: int | None
    customs_records_count: int
    risk_flags: list[str] = field(default_factory=list)
    recommendation: str = "verify_more"


@dataclass
class NegotiationMove:
    """议价单步动作 —— 由 :py:meth:`negotiate` 在每一轮返回。

    - ``move_type``: ``"anchor"`` / ``"concede"`` / ``"trade"`` /
      ``"walk_away"`` —— 与 SYSTEM_PROMPT 中的策略表一一对应。
    - ``proposed_price``: 本轮提价（USD），到 ``walk_away`` 时为最后挂单价。
    - ``proposed_terms``: 配套条件（``payment_term`` / ``moq`` / ``lead_time``
      等），换价用。
    - ``script_text``: 可直接发给供应商的中英文双脚本，前端按供应商语种
      渲染。
    - ``bottom_line_distance_pct``: 当前提价距 target_price 的百分比距离，
      < 5% 时走 close-deal、> 15% 时走 walk-away。
    """

    move_type: str
    proposed_price: float
    proposed_terms: dict
    script_text: str
    rationale: str
    expected_supplier_reaction: str
    bottom_line_distance_pct: float


@dataclass
class ProductSpec:
    """跨平台铺货时使用的商品标准化结构。

    - ``title`` / ``description``: 多语言 dict，``{"zh": ..., "en": ...,
      "ja": ...}`` —— 缺失语种由内容总监 persona 异步补齐。
    - ``hs_code``: 海关编码，影响进口关税与禁限品判定；缺失时只能上架到
      不要求 HS 的平台。
    - ``dimensions_cm``: ``(length, width, height)``。
    - ``weight_g``: 物流计费维度，影响头程报价。
    """

    sku: str
    title: dict[str, str]
    description: dict[str, str]
    price: float
    currency: str
    images: list[str]
    weight_g: float
    dimensions_cm: tuple[float, float, float]
    hs_code: str | None
    origin_country: str


@dataclass
class VATGuidance:
    """指定国家 VAT 申报指引。

    !!!  本类输出 **仅供参考，不构成专业税务建议**。  ``disclaimer`` 字段
         会强制带上"建议联系当地税务师"的提示，前端展示时必须高亮。

    - ``threshold_eur``: 欧盟跨境远程销售起征点（2021 年起为 €10,000，
      整体欧盟联动）；非欧盟国家以本币换算。
    - ``filing_frequency``: ``"monthly"`` / ``"quarterly"`` —— 与目的国
      税务局规定一致；高销售额商家可能被强制按月。
    - ``deadline_pattern``: 自然语言描述（如 ``"次月 10 日前"``），方便
      下游流程管家排日历提醒。
    """

    country: str
    vat_rate_pct: float
    threshold_eur: float
    registration_required: bool
    filing_frequency: str
    deadline_pattern: str
    recommended_steps: list[str]
    forms_to_prepare: list[str]
    disclaimer: str


__all__ = [
    "NicheReport",
    "SupplierVerification",
    "NegotiationMove",
    "ProductSpec",
    "VATGuidance",
]

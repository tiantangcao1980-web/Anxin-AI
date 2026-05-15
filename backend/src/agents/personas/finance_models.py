"""财税顾问 persona — 数据模型（P9-E）。

本模块定义 ``TaxFinanceAdvisorPersona`` 5 大能力（税计算 / 出口退税 /
跨境 VAT / 财报分析 / 税务筹划）输出的强类型 dataclass。

设计取舍
--------
- **dataclass 而非 pydantic**：与 P7-E ``ecommerce_models`` 保持同款约束，
  agent 内部契约保持轻量；API 层通过 ``schemas/persona_finance.py`` 镜像
  到 pydantic。
- **金额字段 float**：和 P7-E 同样的理由 —— 跨平台 JSON 序列化最稳；中国
  境内增值税 / 所得税通常精度到分（小数 2 位）即可，使用 ``round(_, 2)``
  约束输出，不引入 Decimal。
- **citations / disclaimer 一等公民**：税务筹划与跨境 VAT 涉及法规依赖，
  必须可追溯 + 强制免责声明。
- **复用 P7-B Citation**：``research_models.Citation`` 已经在 V3 各 persona
  之间形成事实标准，避免再造一个。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.agents.personas.research_models import Citation


# ---------------------------------------------------------------------------
# 1. 税务计算
# ---------------------------------------------------------------------------
@dataclass
class TaxCalculationRequest:
    """税务计算输入。

    - ``tax_type``: ``"vat"`` / ``"corporate_income"`` /
      ``"individual_income"`` / ``"stamp"`` / ``"consumption"``。
    - ``revenue`` / ``expenses``: 期间收入 / 成本费用（可选，部分税种用
      ``items`` 明细驱动）。
    - ``items``: 明细行（如不同税率的销项 / 不同子项的应税所得），每项
      形如 ``{"name": "...", "amount": ..., "rate_pct": ...}``。
    - ``period``: ``"monthly"`` / ``"quarterly"`` / ``"annual"``。
    - ``region``: 默认 ``"CN"``；后续支持港澳台 / 海外子公司。
    - ``industry``: 行业代码或名（影响所得税优惠 / 加计扣除）。
    - ``special_treatment``: 已享优惠列表（``"high_tech"`` / ``"small_micro"``
      / ``"r_and_d_super_deduction"`` 等），用于触发减免分支。
    """

    tax_type: str
    revenue: float | None = None
    expenses: float | None = None
    items: list[dict] = field(default_factory=list)
    period: str = "monthly"
    region: str = "CN"
    industry: str | None = None
    special_treatment: list[str] = field(default_factory=list)


@dataclass
class TaxCalculationResult:
    """税务计算输出。

    - ``taxable_amount``: 应税基数（销项 / 应纳税所得额 / 应税收入等）。
    - ``tax_rate_pct``: 适用主税率（多税率混合时取加权或主项）。
    - ``tax_payable``: 实际应缴税额（已扣减进项 / 已享优惠后）。
    - ``deductions``: 扣除 / 抵扣明细，每项 ``{"name": ..., "amount": ...,
      "basis": ...}``。
    - ``breakdown``: 自由形态拆解（``{"销项": ..., "进项": ..., "应交": ...}``）。
    - ``legal_basis``: 法条引用（复用 ``Citation``）。
    - ``payment_deadline``: 申报缴款截止日（按 period 推算）。
    - ``notes``: 风险 / 限制 / 假设说明。
    """

    tax_type: str
    taxable_amount: float
    tax_rate_pct: float
    tax_payable: float
    deductions: list[dict] = field(default_factory=list)
    breakdown: dict[str, float] = field(default_factory=dict)
    legal_basis: list[Citation] = field(default_factory=list)
    payment_deadline: date | None = None
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. 出口退税
# ---------------------------------------------------------------------------
@dataclass
class ExportTransaction:
    """单笔出口业务。

    - ``invoice_no``: 出口发票号（专用）。
    - ``hs_code``: 海关 HS 编码 —— 决定退税率档位的关键。
    - ``fob_total_usd``: FOB 离岸价总额（USD），按当月汇率换算 CNY 后
      计算退税基数。
    - ``customs_declaration_no``: 报关单号；与外汇核销 / 退税申报联动。
    """

    invoice_no: str
    product_code: str
    hs_code: str
    quantity: int
    unit_price_usd: float
    fob_total_usd: float
    customs_declaration_no: str
    export_date: date


@dataclass
class RebateReport:
    """出口退税汇总。

    - ``eligible_rebate_amount_cny``: 可退税总金额（CNY）。
    - ``rebate_rate_pct``: 加权退税率（不同 HS 编码可能不同档位）。
    - ``expected_filing_date``: 建议申报日（一般为出口次月 15 日内）。
    - ``required_documents``: 申报所需材料清单（出口发票 / 报关单 /
      装箱单 / 提单 / 收汇凭证 等）。
    - ``risks``: 潜在退税被驳回原因（票货不一致 / 收汇逾期 / HS 误归类）。
    """

    transactions: list[ExportTransaction]
    eligible_rebate_amount_cny: float
    rebate_rate_pct: float
    expected_filing_date: date
    required_documents: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 3. 跨境 VAT
# ---------------------------------------------------------------------------
@dataclass
class VATAdvice:
    """目的国 / 地区 VAT 申报建议。

    与 P7-E ``ecommerce_models.VATGuidance`` 的边界：
        - P7-E ``VATGuidance`` 偏「跨境电商场景」（FBA / 独立站 / B2C），
          强调申报频率与表格清单；
        - 本类 ``VATAdvice`` 偏「制造业财税决策」（含 VAT 应税额预测、
          OSS 适用判断、起征点比对），并给出 ``vat_payable`` 字段，
          可与 ``TaxFinanceAdvisorPersona.calculate_tax`` 对账。

    - ``vat_payable``: 按 ``transaction_amount × vat_rate_pct`` 估算
      应缴 VAT（货币 = ``currency``）。
    - ``needs_oss_registration``: 是否适用 EU OSS 一窗式申报方案
      （年跨境 B2C 销售额 > €10,000 阈值时强制）。
    - ``needs_local_vat_reg``: 是否仍需在目的国本地注册 VAT
      （海外仓 / FBA 等情形通常需要）。
    """

    country: str
    scenario: str
    transaction_amount: float
    currency: str
    vat_rate_pct: float
    vat_payable: float
    threshold_eur: float
    needs_oss_registration: bool
    needs_local_vat_reg: bool
    filing_frequency: str
    deadline_pattern: str
    recommended_steps: list[str] = field(default_factory=list)
    disclaimer: str = ""


# ---------------------------------------------------------------------------
# 4. 财报分析
# ---------------------------------------------------------------------------
@dataclass
class FinancialAnalysis:
    """财报分析结果。

    - ``key_metrics``: 关键财务指标，``{"revenue": ..., "gross_margin":
      ..., "net_margin": ..., "current_ratio": ..., "debt_ratio": ...}``。
    - ``yoy_changes``: 同比变化百分比，``{metric: pct}``。
    - ``health_indicators``: 多指标健康度评估，每项形如
      ``{"name": ..., "value": ..., "benchmark": ..., "status":
      "good"/"warn"/"bad"}``。
    - ``red_flags``: 必须警示的红色信号（应收暴增 / 现金流恶化 /
      毛利倒挂 等）。
    - ``opportunities``: 改善空间（费用结构优化 / 税收筹划机会）。
    - ``overall_health_score``: 0-100 整体健康分（前端环形图）。
    """

    period: str
    summary: str
    key_metrics: dict[str, float] = field(default_factory=dict)
    yoy_changes: dict[str, float] = field(default_factory=dict)
    health_indicators: list[dict] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    overall_health_score: float = 0.0


# ---------------------------------------------------------------------------
# 5. 税务筹划
# ---------------------------------------------------------------------------
@dataclass
class BusinessProfile:
    """企业基础画像（用于税务筹划上下文）。

    - ``is_high_tech`` / ``is_small_micro``: 触发对应的税收优惠分支
      （所得税 15% / 减半征收）。
    - ``has_export``: 触发出口退税路径。
    - ``has_overseas_subsidiary``: 触发 BEPS / CFC 反避税考量。
    """

    industry: str
    annual_revenue: float
    employees: int
    is_high_tech: bool = False
    is_small_micro: bool = False
    has_export: bool = False
    has_overseas_subsidiary: bool = False


@dataclass
class TaxPlanItem:
    """单条税务筹划建议。

    - ``risk_level``: ``"low"`` / ``"medium"`` / ``"high"`` —— 越激进
      （比如核定征收 / 园区返税）风险越高，需明确披露。
    - ``legal_basis``: 法条 / 政策依据，**严禁空缺**，否则该建议不应展示。
    """

    strategy: str
    description: str
    estimated_savings: float
    risk_level: str
    legal_basis: list[Citation] = field(default_factory=list)
    implementation_steps: list[str] = field(default_factory=list)


@dataclass
class TaxPlan:
    """完整年度税务筹划方案。

    - ``current_estimated_tax`` vs ``optimized_estimated_tax`` 之差 =
      ``savings``（可被前端醒目展示，但必须配合 disclaimer）。
    """

    profile: BusinessProfile
    target_year: int
    current_estimated_tax: float
    optimized_estimated_tax: float
    savings: float
    items: list[TaxPlanItem] = field(default_factory=list)
    disclaimer: str = ""


__all__ = [
    "TaxCalculationRequest",
    "TaxCalculationResult",
    "ExportTransaction",
    "RebateReport",
    "VATAdvice",
    "FinancialAnalysis",
    "BusinessProfile",
    "TaxPlanItem",
    "TaxPlan",
]

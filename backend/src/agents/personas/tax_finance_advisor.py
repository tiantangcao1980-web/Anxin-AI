"""财税顾问 persona（P9-E）。

定位：制造业财税一站式智能体 —— 包装 ``tax_compliance.py`` 与
``legal_calculator.py`` 两个 specialized agent，再叠加跨境 VAT 与
财报分析能力，覆盖「税务计算 → 出口退税 → 跨境 VAT → 财报分析 →
税务筹划」全闭环。

设计取舍
--------
- **包装而非重写 specialized agent**：``calculate_tax`` 在生成 LLM 解释
  时优先委派给 ``TaxComplianceAgent``；涉及金额拆解（应纳税所得额 /
  扣除项）则交给 ``LegalCalculatorAgent``，避免双向语义漂移。
- **国家税率 / 起征点写死在常量表**：与 P7-E ``VATGuidance`` 的策略一
  致，离线场景仍能给出确定值，避免 LLM 幻觉抖动。P10+ 接入官方 API
  后改成查询封装即可，dataclass 字段不变。
- **跨境 VAT 边界**：本 persona 关注「制造业出口业务的 VAT 决策」（应缴
  额预测 / 起征点 / OSS 注册判断），P7-E ``EcommerceAssistantAgent.
  vat_guidance`` 关注「跨境电商运营场景的合规步骤」（FBA / 独立站 /
  B2C 申报频率与表格清单）。两者协同而非重复。
- **强制 disclaimer**：税务筹划是高风险输出，``TaxPlan.disclaimer`` 与
  ``VATAdvice.disclaimer`` 都不能为空。
"""

from __future__ import annotations

from datetime import date, timedelta

from src.agents.legal_calculator import LegalCalculatorAgent
from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.finance_models import (
    BusinessProfile,
    ExportTransaction,
    FinancialAnalysis,
    RebateReport,
    TaxCalculationRequest,
    TaxCalculationResult,
    TaxPlan,
    TaxPlanItem,
    VATAdvice,
)
from src.agents.personas.research_models import Citation
from src.agents.tax_compliance import TaxComplianceAgent

# ---------------------------------------------------------------------------
# 中国境内常用税率（与税务总局公开口径对齐 — 仅供财税计算 mock 默认值）
# ---------------------------------------------------------------------------
VAT_STANDARD_RATE_PCT = 13.0
"""增值税一般纳税人销售货物适用主税率 13%。"""

VAT_REDUCED_RATE_PCT = 9.0
"""增值税适用 9% 档（运输、邮政、基础电信、建筑、不动产等）。"""

VAT_SERVICE_RATE_PCT = 6.0
"""增值税适用 6% 档（现代服务、生活服务、金融服务、增值电信等）。"""

CIT_STANDARD_RATE_PCT = 25.0
"""企业所得税法定标准税率 25%。"""

CIT_HIGH_TECH_RATE_PCT = 15.0
"""高新技术企业减按 15% 征收。"""

SMALL_MICRO_THRESHOLD_REVENUE = 3_000_000.0
"""小型微利企业（应纳税所得额 ≤ 300 万）触发减半征收。"""

CIT_SMALL_MICRO_EFFECTIVE_RATE_PCT = 5.0
"""小型微利企业实际综合所得税率（25% × 20% 减计 + 5% 档位汇总，对外简
化口径）。"""

# 出口退税档位（以制造业常见 HS 章节为例，仅作 mock 默认值）
EXPORT_REBATE_RATES_PCT: dict[str, float] = {
    # 机电（84 / 85 章）
    "84": 13.0,
    "85": 13.0,
    # 纺织（50-63）
    "61": 13.0,
    "62": 13.0,
    "63": 13.0,
    # 塑料制品（39 章）
    "39": 13.0,
    # 家具（94 章）
    "94": 13.0,
    # 默认
    "default": 13.0,
}


class TaxFinanceAdvisorPersona(BasePersonaAgent):
    """财税顾问 persona（P9-E）。

    包装 2 个 specialized agent：

    - :class:`src.agents.tax_compliance.TaxComplianceAgent`
      —— 税务合规分析 / 风险评估 / 政策适用。
    - :class:`src.agents.legal_calculator.LegalCalculatorAgent`
      —— 量化分析（赔偿 / 罚款 / 利息），财税场景里用作金额校验底座。
    """

    persona_id = "tax_finance_advisor"
    display_name = "财税顾问"
    emoji = "💰"
    description = "税务合规 + 财务分析 + 跨境 VAT 一站式"
    backed_by_skills = ["xlsx", "docx", "pdf"]
    backed_by_agents = ["tax_compliance", "legal_calculator"]
    supported_apps = ["jindie", "yongyou", "xero", "quickbooks"]
    capabilities = [
        "tax_calculation",
        "export_tax_rebate",
        "cross_border_vat",
        "financial_report_analysis",
        "tax_planning",
    ]

    SYSTEM_PROMPT = """\
你是「财税顾问」💰，制造业企业税务 + 财务一站式智能助手。

核心原则：
1. 法条优先 — 任何税务建议必须给出法律依据（《增值税法》/《企业所得税法》/
   财税字号文件 等），不得凭印象推荐。
2. 数据驱动 — 财报分析、税务筹划都需要真实数据，缺数据时主动追问，不编。
3. 风险分级 — 税务筹划方案要明确标注 risk_level（low/medium/high），
   核定征收 / 园区返税等高风险方案必须额外给出反避税合规警示。
4. 跨境合规 — 涉及出口退税 / 跨境 VAT / 海外子公司时强调当地税务师复核，
   留 7-10 年凭证；EU OSS / 美国 sales tax nexus 等触发条件必须显式判断。
5. 协同优先 — 财税决策与跨境电商运营场景重叠时让跨境电商助手出 VAT
   申报手续清单；财务报表 → 经营策略层面的洞察让市场研究员复核行业基准。

边界：
- 不给出具体逃税 / 偷税建议；不替代持牌税务师 / 注册会计师签字业务。
- 大额筹划方案（节税额 > 100 万）必须提示用户咨询当地主管税务机关。"""

    # ------------------------------------------------------------------
    # 内部 specialized agent 单例（lazy）
    # ------------------------------------------------------------------
    @property
    def _tax_compliance(self) -> TaxComplianceAgent:
        """`tax_compliance` agent lazy 初始化。"""
        if not hasattr(self, "_tax_compliance_inst"):
            try:
                self._tax_compliance_inst = TaxComplianceAgent()
            except Exception:  # pragma: no cover - 防御 LLM client 不可用
                self._tax_compliance_inst = None  # type: ignore[assignment]
        return self._tax_compliance_inst  # type: ignore[return-value]

    @property
    def _legal_calculator(self) -> LegalCalculatorAgent:
        """`legal_calculator` agent lazy 初始化。"""
        if not hasattr(self, "_legal_calculator_inst"):
            try:
                self._legal_calculator_inst = LegalCalculatorAgent()
            except Exception:  # pragma: no cover - 防御
                self._legal_calculator_inst = None  # type: ignore[assignment]
        return self._legal_calculator_inst  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # 能力 1：税务计算
    # ------------------------------------------------------------------
    async def calculate_tax(self, scenario: TaxCalculationRequest) -> TaxCalculationResult:
        """根据税种 + 场景计算应缴税额。

        :param scenario: :class:`TaxCalculationRequest`。
        :raises ValueError: 不支持的税种或缺少必要字段。
        """
        tax_type = (scenario.tax_type or "").lower().strip()
        if tax_type not in {
            "vat",
            "corporate_income",
            "individual_income",
            "stamp",
            "consumption",
        }:
            raise ValueError(f"不支持的税种: {scenario.tax_type}")

        if tax_type == "vat":
            return self._calc_vat(scenario)
        if tax_type == "corporate_income":
            return self._calc_corporate_income(scenario)
        if tax_type == "individual_income":
            return self._calc_individual_income(scenario)
        if tax_type == "stamp":
            return self._calc_stamp(scenario)
        # consumption
        return self._calc_consumption(scenario)

    # ---- 税种子分支 ----
    def _calc_vat(self, scenario: TaxCalculationRequest) -> TaxCalculationResult:
        """增值税：销项 - 进项 = 应交。"""
        items = scenario.items or []
        if items:
            output_tax = sum(
                (i.get("amount", 0) or 0) * (i.get("rate_pct", VAT_STANDARD_RATE_PCT) or 0) / 100
                for i in items
                if i.get("type") != "input"
            )
            input_tax = sum(
                (i.get("amount", 0) or 0) * (i.get("rate_pct", VAT_STANDARD_RATE_PCT) or 0) / 100
                for i in items
                if i.get("type") == "input"
            )
        else:
            revenue = scenario.revenue or 0.0
            expenses = scenario.expenses or 0.0
            output_tax = revenue * VAT_STANDARD_RATE_PCT / 100
            input_tax = expenses * VAT_STANDARD_RATE_PCT / 100

        tax_payable = max(0.0, output_tax - input_tax)
        taxable_amount = scenario.revenue or sum(
            (i.get("amount", 0) or 0) for i in items if i.get("type") != "input"
        )

        return TaxCalculationResult(
            tax_type="vat",
            taxable_amount=round(taxable_amount, 2),
            tax_rate_pct=VAT_STANDARD_RATE_PCT,
            tax_payable=round(tax_payable, 2),
            deductions=[
                {
                    "name": "进项税额抵扣",
                    "amount": round(input_tax, 2),
                    "basis": "增值税一般计税：销项 - 进项",
                }
            ],
            breakdown={
                "output_tax": round(output_tax, 2),
                "input_tax": round(input_tax, 2),
                "tax_payable": round(tax_payable, 2),
            },
            legal_basis=[
                Citation(
                    source="law:vat",
                    url="http://www.chinatax.gov.cn",
                    title="《中华人民共和国增值税法》",
                    excerpt="一般纳税人销售货物适用税率 13%、9%、6%。",
                    confidence=0.9,
                ),
            ],
            payment_deadline=self._next_filing_deadline(scenario.period),
            notes=self._vat_notes(scenario),
        )

    def _calc_corporate_income(self, scenario: TaxCalculationRequest) -> TaxCalculationResult:
        """企业所得税：(收入 - 成本费用) × 适用税率。"""
        revenue = scenario.revenue or 0.0
        expenses = scenario.expenses or 0.0
        taxable_income = max(0.0, revenue - expenses)

        # 优惠分支判定
        is_small_micro = (
            "small_micro" in scenario.special_treatment
            or taxable_income <= SMALL_MICRO_THRESHOLD_REVENUE
        )
        is_high_tech = "high_tech" in scenario.special_treatment

        if is_small_micro:
            rate = CIT_SMALL_MICRO_EFFECTIVE_RATE_PCT
            basis_excerpt = "小型微利企业减按 5% 综合实际税率（财税 2023.12 号公告）。"
        elif is_high_tech:
            rate = CIT_HIGH_TECH_RATE_PCT
            basis_excerpt = "高新技术企业减按 15% 征收（《企业所得税法》第二十八条）。"
        else:
            rate = CIT_STANDARD_RATE_PCT
            basis_excerpt = "企业所得税法定税率 25%（《企业所得税法》第四条）。"

        tax_payable = taxable_income * rate / 100

        return TaxCalculationResult(
            tax_type="corporate_income",
            taxable_amount=round(taxable_income, 2),
            tax_rate_pct=rate,
            tax_payable=round(tax_payable, 2),
            deductions=[
                {
                    "name": "成本费用扣除",
                    "amount": round(expenses, 2),
                    "basis": "据实扣除",
                }
            ],
            breakdown={
                "revenue": round(revenue, 2),
                "expenses": round(expenses, 2),
                "taxable_income": round(taxable_income, 2),
                "tax_payable": round(tax_payable, 2),
            },
            legal_basis=[
                Citation(
                    source="law:cit",
                    url="http://www.chinatax.gov.cn",
                    title="《中华人民共和国企业所得税法》",
                    excerpt=basis_excerpt,
                    confidence=0.9,
                )
            ],
            payment_deadline=self._next_filing_deadline(scenario.period),
            notes=[
                "本计算基于会计利润简化推算，未考虑纳税调整事项。",
                "实际申报需按 A 类年度纳税申报表逐项填列。",
            ],
        )

    def _calc_individual_income(self, scenario: TaxCalculationRequest) -> TaxCalculationResult:
        """个税（综合所得简化版）：年应纳税所得额超额累进。"""
        annual_income = scenario.revenue or 0.0
        # 5000/月 × 12 = 60000 基本减除费用
        taxable = max(0.0, annual_income - 60_000 - (scenario.expenses or 0.0))

        # 综合所得 7 档税率（速算扣除数）
        brackets = [
            (36_000, 3, 0),
            (144_000, 10, 2520),
            (300_000, 20, 16920),
            (420_000, 25, 31920),
            (660_000, 30, 52920),
            (960_000, 35, 85920),
            (float("inf"), 45, 181920),
        ]
        for upper, rate_pct, deduction in brackets:
            if taxable <= upper:
                tax = taxable * rate_pct / 100 - deduction
                applied_rate = rate_pct
                break
        else:  # pragma: no cover - 兜底
            applied_rate = 45
            tax = taxable * 0.45 - 181920

        tax_payable = max(0.0, tax)

        return TaxCalculationResult(
            tax_type="individual_income",
            taxable_amount=round(taxable, 2),
            tax_rate_pct=float(applied_rate),
            tax_payable=round(tax_payable, 2),
            deductions=[
                {"name": "基本减除费用", "amount": 60_000, "basis": "5000/月 × 12"},
                {
                    "name": "专项 / 专项附加",
                    "amount": round(scenario.expenses or 0.0, 2),
                    "basis": "据实填列",
                },
            ],
            breakdown={
                "annual_income": round(annual_income, 2),
                "taxable": round(taxable, 2),
                "tax_payable": round(tax_payable, 2),
            },
            legal_basis=[
                Citation(
                    source="law:iit",
                    url="http://www.chinatax.gov.cn",
                    title="《中华人民共和国个人所得税法》",
                    excerpt="综合所得适用 3-45% 七级超额累进税率。",
                    confidence=0.9,
                )
            ],
            payment_deadline=date(date.today().year + 1, 6, 30),
            notes=["本计算未含年终奖单独计税选项；综合 vs 单独可优化对比。"],
        )

    def _calc_stamp(self, scenario: TaxCalculationRequest) -> TaxCalculationResult:
        """印花税：合同金额 × 万分之三（默认）。"""
        amount = scenario.revenue or 0.0
        rate = 0.03  # 万分之三 = 0.03%
        tax = amount * rate / 100
        return TaxCalculationResult(
            tax_type="stamp",
            taxable_amount=round(amount, 2),
            tax_rate_pct=rate,
            tax_payable=round(tax, 2),
            breakdown={"contract_amount": round(amount, 2), "tax": round(tax, 2)},
            legal_basis=[
                Citation(
                    source="law:stamp",
                    url="http://www.chinatax.gov.cn",
                    title="《中华人民共和国印花税法》",
                    excerpt="购销合同税率万分之三。",
                    confidence=0.9,
                )
            ],
            payment_deadline=self._next_filing_deadline(scenario.period),
            notes=["不同合同类型税率不同，借款合同万分之零点五，租赁千分之一。"],
        )

    def _calc_consumption(self, scenario: TaxCalculationRequest) -> TaxCalculationResult:
        """消费税：从价/从量/复合计征。"""
        amount = scenario.revenue or 0.0
        # 简化：从价 10%（化妆品 / 摩托车等档位的中位数）
        rate = 10.0
        tax = amount * rate / 100
        return TaxCalculationResult(
            tax_type="consumption",
            taxable_amount=round(amount, 2),
            tax_rate_pct=rate,
            tax_payable=round(tax, 2),
            breakdown={"sales": round(amount, 2), "tax": round(tax, 2)},
            legal_basis=[
                Citation(
                    source="law:consumption",
                    url="http://www.chinatax.gov.cn",
                    title="《中华人民共和国消费税暂行条例》",
                    excerpt="化妆品 / 摩托车等适用 10% 档位。",
                    confidence=0.85,
                )
            ],
            payment_deadline=self._next_filing_deadline(scenario.period),
            notes=["实际税率因税目差异较大（烟酒高、汽车低），仅供参考。"],
        )

    def _vat_notes(self, scenario: TaxCalculationRequest) -> list[str]:
        notes = []
        if "small_scale" in scenario.special_treatment:
            notes.append("小规模纳税人按 3% 征收率简易计税（疫情减免至 1%）。")
        if scenario.region != "CN":
            notes.append(f"region={scenario.region}：跨境业务请同步检查目的国 VAT。")
        return notes

    def _next_filing_deadline(self, period: str) -> date:
        """根据 period 推算下一申报截止日（与征管法对齐）。"""
        today = date.today()
        if period == "monthly":
            # 次月 15 日
            year = today.year + (1 if today.month == 12 else 0)
            month = 1 if today.month == 12 else today.month + 1
            return date(year, month, 15)
        if period == "quarterly":
            # 季后次月 15 日（粗略实现）
            return today + timedelta(days=45)
        # annual
        return date(today.year + 1, 5, 31)

    # ------------------------------------------------------------------
    # 能力 2：出口退税
    # ------------------------------------------------------------------
    async def export_tax_rebate(self, exports: list[ExportTransaction]) -> RebateReport:
        """计算出口退税总额 + 申报材料清单。

        :param exports: 多笔出口业务。
        :raises ValueError: ``exports`` 为空。
        """
        if not exports:
            raise ValueError("exports 不能为空")

        # 汇率简化：1 USD = 7.10 CNY（mock；P10 接入央行汇率 API）
        usd_to_cny = 7.10

        total_fob_cny = 0.0
        weighted_rebate_cny = 0.0
        for tx in exports:
            chapter = tx.hs_code[:2] if tx.hs_code else "default"
            rate_pct = EXPORT_REBATE_RATES_PCT.get(chapter, EXPORT_REBATE_RATES_PCT["default"])
            fob_cny = tx.fob_total_usd * usd_to_cny
            total_fob_cny += fob_cny
            weighted_rebate_cny += fob_cny * rate_pct / 100

        weighted_rate = weighted_rebate_cny / total_fob_cny * 100 if total_fob_cny > 0 else 0.0

        latest_export_date = max(tx.export_date for tx in exports)
        # 出口次月 15 日内申报
        next_month = latest_export_date.month % 12 + 1
        year = latest_export_date.year + (1 if latest_export_date.month == 12 else 0)
        expected_filing = date(year, next_month, 15)

        risks: list[str] = []
        if any(not tx.customs_declaration_no for tx in exports):
            risks.append("部分出口业务缺少报关单号，将被税务机关驳回退税申请")
        if any(tx.fob_total_usd <= 0 for tx in exports):
            risks.append("FOB 金额异常（≤0），需核对出口发票")

        return RebateReport(
            transactions=exports,
            eligible_rebate_amount_cny=round(weighted_rebate_cny, 2),
            rebate_rate_pct=round(weighted_rate, 2),
            expected_filing_date=expected_filing,
            required_documents=[
                "出口货物报关单",
                "出口发票",
                "出口收汇核销单 / 银行收汇凭证",
                "海运 / 空运提单",
                "装箱单",
                "购进货物增值税专用发票",
                "出口退税申报汇总表",
            ],
            risks=risks,
        )

    # ------------------------------------------------------------------
    # 能力 3：跨境 VAT 指引
    # ------------------------------------------------------------------
    async def cross_border_vat_guidance(
        self,
        country: str,
        scenario: str,
        amount: float,
        currency: str,
    ) -> VATAdvice:
        """跨境 VAT 决策建议（含应缴预测 + OSS 判断）。

        与 P7-E ``EcommerceAssistantAgent.vat_guidance`` 的边界：本方法
        额外给出 ``vat_payable`` 与 ``needs_oss_registration`` 等决策字段，
        适合财务部门做应缴金额预算与注册路径选择。
        """
        if amount < 0:
            raise ValueError("amount 必须 >= 0")

        country_norm = country.strip().upper()
        # (rate, threshold_eur, freq, deadline, in_eu)
        kb: dict[str, tuple[float, float, str, str, bool]] = {
            "DE": (19.0, 10000.0, "monthly", "次月 10 日前", True),
            "GERMANY": (19.0, 10000.0, "monthly", "次月 10 日前", True),
            "德国": (19.0, 10000.0, "monthly", "次月 10 日前", True),
            "FR": (20.0, 10000.0, "monthly", "次月 19 日前", True),
            "FRANCE": (20.0, 10000.0, "monthly", "次月 19 日前", True),
            "法国": (20.0, 10000.0, "monthly", "次月 19 日前", True),
            "IT": (22.0, 10000.0, "monthly", "次月 16 日前", True),
            "ITALY": (22.0, 10000.0, "monthly", "次月 16 日前", True),
            "意大利": (22.0, 10000.0, "monthly", "次月 16 日前", True),
            "ES": (21.0, 10000.0, "monthly", "次月 30 日前", True),
            "SPAIN": (21.0, 10000.0, "monthly", "次月 30 日前", True),
            "西班牙": (21.0, 10000.0, "monthly", "次月 30 日前", True),
            "UK": (20.0, 0.0, "quarterly", "季后 1 个月零 7 天", False),
            "ENGLAND": (20.0, 0.0, "quarterly", "季后 1 个月零 7 天", False),
            "英国": (20.0, 0.0, "quarterly", "季后 1 个月零 7 天", False),
            "US": (0.0, 0.0, "quarterly", "各州不一", False),
            "美国": (0.0, 0.0, "quarterly", "各州不一", False),
        }
        rate, threshold, freq, deadline, in_eu = kb.get(
            country_norm, (20.0, 10000.0, "quarterly", "请咨询当地税务师", False)
        )

        vat_payable = amount * rate / 100

        # OSS 适用判断：欧盟成员国 + B2C 跨境远程销售 + 销售额超阈值
        is_b2c = "B2C" in scenario.upper() or "电商" in scenario or "独立站" in scenario
        amount_eur = amount  # 简化：假定 currency = EUR；非欧元需汇率换算
        needs_oss = in_eu and is_b2c and amount_eur > threshold
        needs_local = not in_eu or "FBA" in scenario.upper() or "海外仓" in scenario

        steps: list[str] = []
        if needs_oss:
            steps.append("在原籍国（如荷兰 / 爱尔兰）注册 EU OSS 一窗式申报方案")
            steps.append("通过 OSS 系统按季度统一申报欧盟各国 VAT")
        if needs_local:
            steps.append(f"在 {country} 注册本地 VAT 号（建议委托当地税务代表）")
        steps.extend(
            [
                f"按 {freq} 频率申报，截止：{deadline}",
                f"配置 ERP 中 {country} VAT 税率为 {rate:.1f}%",
                "保留进口单据 + 销售单据 + 运单 7-10 年",
            ]
        )
        if country_norm in {"US", "美国", "USA"}:
            steps = [
                "判断 nexus 触发的州（仓储 / 销售额 / 雇员所在州）",
                "在触发州申请 sales tax permit",
                "按州周期申报（多数为月报或季报）",
            ]

        disclaimer = (
            "⚠️ 本指引仅供参考，不构成专业税务或法律意见。VAT/Sales Tax 法规变化频繁，"
            "且不同业务模式（FBA/海外仓/独立站直邮/B2B/B2C）适用规则不同。请委托目的国"
            "持牌税务师确认后再行操作；安心智能助手不承担依据本指引产生的税务风险。"
        )

        return VATAdvice(
            country=country,
            scenario=scenario,
            transaction_amount=round(amount, 2),
            currency=currency,
            vat_rate_pct=rate,
            vat_payable=round(vat_payable, 2),
            threshold_eur=threshold,
            needs_oss_registration=needs_oss,
            needs_local_vat_reg=needs_local,
            filing_frequency=freq,
            deadline_pattern=deadline,
            recommended_steps=steps,
            disclaimer=disclaimer,
        )

    # ------------------------------------------------------------------
    # 能力 4：财报分析
    # ------------------------------------------------------------------
    async def analyze_financial_report(self, report_text_or_excel_path: str) -> FinancialAnalysis:
        """财报分析（健康度评分 + 红色信号 + 优化机会）。

        当前阶段返回基于关键词的轻量启发式分析；P10+ 接入 xlsx skill
        + 财务比率引擎后给出真实财报数据。
        """
        text = report_text_or_excel_path or ""
        is_excel = text.endswith(".xlsx") or text.endswith(".xls")

        # 启发式：从文本里提取负面 / 正面信号
        red_flags: list[str] = []
        opportunities: list[str] = []

        if "应收" in text and ("增" in text or "暴" in text):
            red_flags.append("应收账款增长过快，警惕坏账风险")
        if "现金流" in text and ("负" in text or "恶化" in text):
            red_flags.append("经营性现金流为负，资金链承压")
        if "毛利" in text and "倒挂" in text:
            red_flags.append("毛利率倒挂，主营业务出现亏损")
        if "存货" in text and ("积压" in text or "增" in text):
            red_flags.append("存货周转减慢，潜在跌价准备")

        if "研发" in text:
            opportunities.append("研发费用加计扣除（100% 加计扣除政策）可降低所得税基")
        if "出口" in text:
            opportunities.append("出口业务可申请退税，建议核对 HS 编码档位")
        if "高新" not in text and "技术" in text:
            opportunities.append("符合条件可申请高新技术企业认定，所得税降至 15%")

        # 简化的关键指标（mock）
        key_metrics = {
            "revenue": 100_000_000.0,
            "gross_margin": 28.5,
            "net_margin": 8.2,
            "current_ratio": 1.6,
            "debt_ratio": 52.0,
        }
        yoy_changes = {
            "revenue": 12.5,
            "gross_margin": -2.3,
            "net_margin": -1.5,
            "current_ratio": -0.1,
            "debt_ratio": 3.0,
        }
        health_indicators = [
            {
                "name": "毛利率",
                "value": key_metrics["gross_margin"],
                "benchmark": 30.0,
                "status": "warn",
            },
            {
                "name": "净利率",
                "value": key_metrics["net_margin"],
                "benchmark": 10.0,
                "status": "warn",
            },
            {
                "name": "流动比率",
                "value": key_metrics["current_ratio"],
                "benchmark": 2.0,
                "status": "warn",
            },
            {
                "name": "资产负债率",
                "value": key_metrics["debt_ratio"],
                "benchmark": 50.0,
                "status": "warn",
            },
        ]

        # 评分：每个 red_flag -10，每个 opportunity +3，基线 75
        score = 75 - 10 * len(red_flags) + 3 * len(opportunities)
        score = max(0.0, min(100.0, float(score)))

        summary_prefix = "（基于 Excel 财报）" if is_excel else "（基于文本财报）"
        summary = (
            f"{summary_prefix}收入同比 +{yoy_changes['revenue']:.1f}%，"
            f"毛利率 {key_metrics['gross_margin']:.1f}%，净利率 "
            f"{key_metrics['net_margin']:.1f}%。整体健康度 {score:.0f} 分。"
        )

        return FinancialAnalysis(
            period="2025年度",
            summary=summary,
            key_metrics=key_metrics,
            yoy_changes=yoy_changes,
            health_indicators=health_indicators,
            red_flags=red_flags,
            opportunities=opportunities,
            overall_health_score=score,
        )

    # ------------------------------------------------------------------
    # 能力 5：税务筹划
    # ------------------------------------------------------------------
    async def tax_planning(
        self,
        business_profile: BusinessProfile,
        target_year: int,
    ) -> TaxPlan:
        """生成年度税务筹划方案。

        :raises ValueError: ``target_year`` 必须 ≥ 当前年。
        """
        if target_year < date.today().year:
            raise ValueError("target_year 必须 ≥ 当前年度")

        # 当前估算应缴：所得税 + 增值税（粗略）
        revenue = business_profile.annual_revenue
        # 假设成本费用 = 收入 × 75%
        expenses = revenue * 0.75
        taxable_income = max(0.0, revenue - expenses)

        if business_profile.is_high_tech:
            current_cit_rate = CIT_HIGH_TECH_RATE_PCT
        else:
            current_cit_rate = CIT_STANDARD_RATE_PCT
        current_cit = taxable_income * current_cit_rate / 100
        # 增值税净税负 ~= 收入 × 13% - 进项 ~= 收入 × 3%（粗估）
        current_vat = revenue * 0.03
        current_total = current_cit + current_vat

        items: list[TaxPlanItem] = []

        # 策略 1：研发费用加计扣除（100%）
        if not business_profile.is_high_tech:
            r_and_d = revenue * 0.05  # 假设研发投入占收入 5%
            saving = r_and_d * current_cit_rate / 100  # 加计扣除等额
            items.append(
                TaxPlanItem(
                    strategy="研发费用 100% 加计扣除",
                    description=(
                        f"假设研发投入约 {r_and_d:,.0f} 元，按 100% 加计扣除可减少"
                        f"应纳税所得额 {r_and_d:,.0f} 元，节税约 {saving:,.0f} 元。"
                    ),
                    estimated_savings=round(saving, 2),
                    risk_level="low",
                    legal_basis=[
                        Citation(
                            source="law:cit",
                            url="http://www.chinatax.gov.cn",
                            title="财政部 税务总局公告 2023 年第 7 号",
                            excerpt="制造业企业研发费用按 100% 加计扣除政策延续。",
                            confidence=0.95,
                        )
                    ],
                    implementation_steps=[
                        "建立研发项目台账与立项备案",
                        "归集研发人员薪酬、直接投入、折旧等",
                        "年度汇算清缴时填报 A107012 研发费用加计扣除明细表",
                    ],
                )
            )

        # 策略 2：高新技术企业认定
        if not business_profile.is_high_tech and business_profile.industry in {
            "manufacturing",
            "tech",
            "制造业",
            "高新技术",
        }:
            saving = taxable_income * (CIT_STANDARD_RATE_PCT - CIT_HIGH_TECH_RATE_PCT) / 100
            items.append(
                TaxPlanItem(
                    strategy="高新技术企业认定",
                    description=(
                        "若通过高新技术企业认定，企业所得税从 25% 降至 15%，"
                        f"预计每年节税 {saving:,.0f} 元。"
                    ),
                    estimated_savings=round(saving, 2),
                    risk_level="medium",
                    legal_basis=[
                        Citation(
                            source="law:cit",
                            url="http://www.chinatax.gov.cn",
                            title="《企业所得税法》第二十八条",
                            excerpt="国家需要重点扶持的高新技术企业减按 15% 征收。",
                            confidence=0.9,
                        )
                    ],
                    implementation_steps=[
                        "梳理近三年研发费用占比、知识产权、科技人员比例",
                        "委托认定咨询机构准备申报材料",
                        "通过省级科技 / 财税 / 税务三部门联合认定",
                    ],
                )
            )

        # 策略 3：出口退税（若有出口）
        if business_profile.has_export:
            export_amount = revenue * 0.30  # 假设出口占 30%
            saving = export_amount * 13.0 / 100  # 13% 退税率
            items.append(
                TaxPlanItem(
                    strategy="出口退税应退尽退",
                    description=(
                        f"出口业务约 {export_amount:,.0f} 元，按 13% 平均退税率"
                        f"可退税约 {saving:,.0f} 元。"
                    ),
                    estimated_savings=round(saving, 2),
                    risk_level="low",
                    legal_basis=[
                        Citation(
                            source="law:vat",
                            url="http://www.chinatax.gov.cn",
                            title="《增值税出口退（免）税管理办法》",
                            excerpt="生产企业自营出口适用免抵退税。",
                            confidence=0.9,
                        )
                    ],
                    implementation_steps=[
                        "确认 HS 编码对应退税率",
                        "出口次月 15 日内申报",
                        "保留报关单 + 出口发票 + 收汇凭证 7 年",
                    ],
                )
            )

        # 策略 4：跨境利润转移合规（仅警示）
        if business_profile.has_overseas_subsidiary:
            items.append(
                TaxPlanItem(
                    strategy="海外子公司转让定价合规",
                    description=(
                        "海外子公司间关联交易必须满足独立交易原则；建议同期资料"
                        "齐全，避免被认定 BEPS 反避税调整。"
                    ),
                    estimated_savings=0.0,
                    risk_level="high",
                    legal_basis=[
                        Citation(
                            source="law:cit",
                            url="http://www.chinatax.gov.cn",
                            title="《特别纳税调整实施办法》",
                            excerpt="关联交易应符合独立交易原则。",
                            confidence=0.9,
                        )
                    ],
                    implementation_steps=[
                        "编制本地文档 + 主体文档 + 国别报告（CbCR）",
                        "评估转让定价方法（CUP / RPM / TNMM）",
                        "必要时申请预约定价安排（APA）",
                    ],
                )
            )

        savings_total = sum(i.estimated_savings for i in items)
        optimized = max(0.0, current_total - savings_total)

        disclaimer = (
            "⚠️ 本筹划方案基于公开税收政策与典型场景假设生成，仅供参考，不构成"
            "专业税务意见。具体落地必须委托当地持牌税务师 / 会计师事务所复核；"
            "节税额超过 100 万的方案建议提前与主管税务机关沟通，避免被认定避税。"
        )

        return TaxPlan(
            profile=business_profile,
            target_year=target_year,
            current_estimated_tax=round(current_total, 2),
            optimized_estimated_tax=round(optimized, 2),
            savings=round(savings_total, 2),
            items=items,
            disclaimer=disclaimer,
        )

    # ------------------------------------------------------------------
    # 工具：报税日历
    # ------------------------------------------------------------------
    def filing_calendar(self, region: str, year: int) -> list[dict]:
        """生成报税日历（按月）。"""
        calendar = []
        for month in range(1, 13):
            calendar.append(
                {
                    "month": month,
                    "deadlines": [
                        {
                            "type": "增值税 / 附加税",
                            "date": f"{year}-{month:02d}-15",
                        },
                        {
                            "type": "个人所得税（代扣代缴）",
                            "date": f"{year}-{month:02d}-15",
                        },
                    ],
                }
            )
        # 年度汇算
        calendar[4]["deadlines"].append(
            {"type": "企业所得税年度汇算清缴（截止 5 月 31 日）", "date": f"{year}-05-31"}
        )
        calendar[5]["deadlines"].append(
            {"type": "个人所得税综合所得汇算（截止 6 月 30 日）", "date": f"{year}-06-30"}
        )
        return calendar


__all__ = [
    "TaxFinanceAdvisorPersona",
    "VAT_STANDARD_RATE_PCT",
    "VAT_REDUCED_RATE_PCT",
    "VAT_SERVICE_RATE_PCT",
    "CIT_STANDARD_RATE_PCT",
    "CIT_HIGH_TECH_RATE_PCT",
    "CIT_SMALL_MICRO_EFFECTIVE_RATE_PCT",
    "SMALL_MICRO_THRESHOLD_REVENUE",
    "EXPORT_REBATE_RATES_PCT",
]

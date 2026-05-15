"""跨境电商助手 persona（P7-E）。

定位：制造业出海全链路智能体 —— 从「想做出海」到「第一笔订单回款」之间的
所有动作（选品 / 验商 / 议价 / 建站 / 铺货 / VAT 合规）都在一个 persona
里完成路由。

设计取舍
--------
- **6 个能力 = 6 个独立方法**：方便上层 capability registry 按 skill 路由，
  也方便单元测试隔离断言。
- **AI 议价用确定性算法 + LLM 文案**：定价让步走规则引擎（保证单调和兜底），
  谈判文案让 LLM 生成（保证语种自然）；这样 ``walk_away`` 阈值可被压力测试。
- **LLM 调用通过 ``self._llm_chat`` 适配层**：未来 ``BasePersonaAgent`` 提供
  真实 chat 后只需替换该 helper，6 个能力方法不必改签名。
- **mock 数据贯穿**：在 LLM / OAuth 不可用（CI / 离线开发）时，每个能力
  都返回结构化 mock，保证下游集成测试不被阻塞。
"""

from __future__ import annotations

from typing import Any

from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.ecommerce_models import (
    NegotiationMove,
    NicheReport,
    ProductSpec,
    SupplierVerification,
    VATGuidance,
)

# ---------------------------------------------------------------------------
# 议价策略常量（暴露在模块级，方便测试 import 调阈值）
# ---------------------------------------------------------------------------
ANCHOR_DISCOUNT_PCT = 30.0
"""第一轮锚定相对 target_price 的折扣 —— anchoring bias，给后续让步留空间。"""

CONCEDE_STEP_AGGRESSIVE = 5.0
CONCEDE_STEP_MODERATE = 7.0
CONCEDE_STEP_FRIENDLY = 10.0
"""每轮让步幅度（按 mood 分档），单位 = target_price 的百分比。"""

CLOSE_DEAL_BAND_PCT = 5.0
"""距 target_price ±5% 内 = 收口；不再让步，直接确认。"""

WALK_AWAY_THRESHOLD_PCT = 15.0
"""提价超过 target_price + 15% 时走 walk_away。

阈值选择理由：
- 跨境制造业普遍利润率 8–18%，超过 15% 意味着已经吃掉全部利润 + 部分本金。
- 留 15% 而不是 10% 是因为前几轮 anchor 在 -30%，正常对齐空间在 ±10%；
  walk_away 在更外侧避免「友好谈判」过早翻脸。
- 留 15% 而不是 20% 是因为再让一步对方很可能继续压，止损必须明确。
"""

TRADE_AFTER_ROUND = 3
"""第 4 轮起优先 ``trade``（用 MOQ / 付款方式 / 长期合作 换价）。"""


class EcommerceAssistantAgent(BasePersonaAgent):
    """跨境电商助手 persona。

    与 P6-D ecommerce sources 协同：``analyze_niche`` / ``verify_supplier``
    / ``list_to_platforms`` 在真实接入时会通过 FetchService 调用对应 source；
    本 P7-E 阶段返回结构化 mock，确保接口契约稳定。
    """

    persona_id = "ecommerce_assistant"
    display_name = "跨境电商助手"
    emoji = "🌍"
    description = "出海全链路：选品/议价/独立站/铺货/VAT 合规"
    backed_by_skills = ["xlsx", "docx", "pptx", "pdf"]
    supported_apps = ["shopify", "amazon_sp", "alibaba_1688", "shopee", "tiktok_shop"]
    capabilities = [
        "product_sourcing_analysis",
        "supplier_verification",
        "ai_bargaining",
        "store_setup",
        "multi_platform_listing",
        "vat_compliance",
    ]

    SYSTEM_PROMPT = """\
你是「跨境电商助手」🌍，定位是制造业出海全链路顾问。

核心原则：
1. 数据驱动 — 选品 / 验商必须给数据来源（citations），不得凭印象推荐。
2. 风险优先 — 红海赛道、低利润率、专利风险一律标红，宁可让用户 wait/skip
   也不让用户跳坑。
3. 议价克制 — 中国制造业供应商关系是长期资产；让步策略追求「双方都觉得
   赢」而非压死对方。
4. 合规边界 — VAT / 进出口许可属于专业领域，必须给出 disclaimer，建议
   联系当地税务师 / 律师确认。
5. 协同优先 — 涉及多语言营销让内容总监出手；涉及税务让财税顾问复核；
   涉及跨境合规让法律顾问把关。"""

    # ------------------------------------------------------------------
    # LLM 适配层（stub）
    # ------------------------------------------------------------------
    async def _llm_chat(self, prompt: str, **_: Any) -> str:  # pragma: no cover
        """真实 BasePersonaAgent 注入 chat 后接管；当前阶段返回空串。"""
        return ""

    # ------------------------------------------------------------------
    # 能力 1：选品分析
    # ------------------------------------------------------------------
    async def analyze_niche(
        self,
        niche: str,
        target_markets: list[str],
    ) -> NicheReport:
        """对一个细分赛道做市场调研 + 风险评估。

        :param niche: 自然语言的细分品类名（例：``"瑜伽垫"``）。
        :param target_markets: 目标市场国家代码列表（``["US", "DE", "JP"]``）。

        返回包含：
        - market_size_usd / growth_rate_pct（来自亚马逊 BSR + Google Trends）
        - competition_level / avg_price_band（Top 10 卖家利润率聚合）
        - top_competitors（含 ASIN / Shop Domain / 估算月销）
        - recommended_action ∈ {enter, wait, skip}

        当前阶段返回 mock；P8 会接入 P6-D Amazon SP-API + Shopify search。
        """
        # P8 真实接入：FetchService.fetch(EcommerceSource.amazon_sp.search) ...
        # 当前 mock：基于 niche 关键词给一个保守的 enter / wait / skip 提示。
        is_red_ocean = any(k in niche for k in ["瑜伽垫", "数据线", "充电宝", "口罩"])
        is_emerging = any(k in niche for k in ["碳纤维", "便携", "可折叠", "智能"])

        if is_red_ocean and not is_emerging:
            action = "wait"
            rationale = "Top 10 卖家利润率压到 8%，红海化明显；建议加观察列表 30 天再判断。"
            margin = 8.0
        elif is_emerging:
            action = "enter"
            rationale = "差异化机会窗口，建议小批量首单（≤500 件）试水。"
            margin = 22.0
        else:
            action = "wait"
            rationale = "数据样本不足以判断红海/蓝海，建议接入 P6-D ecommerce sources 后复评。"
            margin = 15.0

        return NicheReport(
            niche=niche,
            market_size_usd=12_500_000.0,
            growth_rate_pct=18.5,
            competition_level="high" if is_red_ocean else "medium",
            avg_price_band=(15.0, 45.0),
            profit_margin_estimate_pct=margin,
            top_competitors=[
                {"asin": "B0XXXXXXX1", "monthly_sales_est": 8000, "price_usd": 22.99},
                {"asin": "B0XXXXXXX2", "monthly_sales_est": 5500, "price_usd": 28.50},
                {"asin": "B0XXXXXXX3", "monthly_sales_est": 3200, "price_usd": 35.00},
            ],
            seasonal_pattern="Q4 holiday spike +35%",
            recommended_action=action,
            rationale=rationale,
            citations=[
                {
                    "source": "amazon_sp",
                    "url": f"https://www.amazon.com/s?k={niche}",
                    "snippet": f"{niche} BSR top results (mock)",
                },
                {
                    "source": "google_trends",
                    "url": f"https://trends.google.com/trends/explore?q={niche}",
                    "snippet": "Past 12 months interest (mock)",
                },
            ],
        )

    # ------------------------------------------------------------------
    # 能力 2：供应商验真
    # ------------------------------------------------------------------
    async def verify_supplier(
        self,
        supplier_id_or_url: str,
        source: str = "alibaba_1688",
    ) -> SupplierVerification:
        """验证供应商资质 / 信用 / 出货能力。

        :param supplier_id_or_url: 1688 / 阿里国际站的厂家 ID 或店铺 URL。
        :param source: 数据来源平台 ID，默认 ``"alibaba_1688"``。

        当前阶段返回 mock；P8 接入 1688 开放平台 + 海关公开数据 + 启信宝。
        """
        # P8 真实接入：调用 P6-D alibaba_1688 source.get_supplier(...)
        # 配合 P6-A FetchService 抓海关公开数据。
        is_suspicious = "test" in supplier_id_or_url.lower() or "demo" in supplier_id_or_url.lower()

        return SupplierVerification(
            supplier_id=supplier_id_or_url,
            name="深圳市XX精密制造有限公司",
            business_license_verified=not is_suspicious,
            factory_audit_grade="B" if not is_suspicious else None,
            years_in_business=7 if not is_suspicious else 1,
            moq=500,
            capacity_per_month=20_000 if not is_suspicious else None,
            customs_records_count=42 if not is_suspicious else 0,
            risk_flags=[] if not is_suspicious else ["recently_registered", "no_audit"],
            recommendation="trust" if not is_suspicious else "avoid",
        )

    # ------------------------------------------------------------------
    # 能力 3：AI 议价（多轮策略）
    # ------------------------------------------------------------------
    async def negotiate(
        self,
        target_price: float,
        mood: str,
        history: list[dict],
    ) -> NegotiationMove:
        """生成下一轮议价动作。

        策略表（与 ``WALK_AWAY_THRESHOLD_PCT`` 等模块常量对齐）::

            Round 1            anchor 在 target_price - 30%
            Round 2-3          按 mood 让 5/7/10% / 轮，要求供应商对等让步
            Round 4+           优先 trade（MOQ / 付款方式 / 长期合作 换价）
            ±5% 收口            close deal（move_type 仍标 concede）
            +15% 越线           walk_away

        :param target_price: 我方理想价（USD）。
        :param mood: ``"aggressive"`` / ``"moderate"`` / ``"friendly"``。
        :param history: 历史轮次，每项形如
            ``{"round": 1, "our_price": ..., "their_price": ...}``。

        :raises ValueError: ``mood`` 取值非法、``target_price <= 0``。
        """
        if target_price <= 0:
            raise ValueError("target_price 必须 > 0")
        if mood not in {"aggressive", "moderate", "friendly"}:
            raise ValueError(f"非法 mood: {mood}")

        round_num = len(history) + 1
        last_their_price = (
            history[-1].get("their_price") if history else None
        )

        # ---- walk_away：对方报价 > target * (1 + 15%) ----
        if last_their_price is not None and last_their_price > target_price * (
            1 + WALK_AWAY_THRESHOLD_PCT / 100
        ):
            distance = (last_their_price - target_price) / target_price * 100
            return self._build_walk_away(target_price, last_their_price, distance)

        # ---- close_deal：双方报价已在 ±5% 内 ----
        if last_their_price is not None:
            gap_pct = abs(last_their_price - target_price) / target_price * 100
            if gap_pct <= CLOSE_DEAL_BAND_PCT:
                return self._build_close(target_price, last_their_price, gap_pct)

        # ---- Round 1：anchor ----
        if round_num == 1:
            our_price = target_price * (1 - ANCHOR_DISCOUNT_PCT / 100)
            return self._build_anchor(our_price, target_price)

        # ---- Round 4+：trade ----
        if round_num >= TRADE_AFTER_ROUND + 1:
            return self._build_trade(target_price, last_their_price or target_price * 1.1)

        # ---- Round 2-3：concede ----
        step_pct = {
            "aggressive": CONCEDE_STEP_AGGRESSIVE,
            "moderate": CONCEDE_STEP_MODERATE,
            "friendly": CONCEDE_STEP_FRIENDLY,
        }[mood]
        last_our_price = history[-1].get("our_price", target_price * (1 - ANCHOR_DISCOUNT_PCT / 100))
        our_price = last_our_price + target_price * (step_pct / 100)
        # 不超过 target，否则没法继续谈
        our_price = min(our_price, target_price * 0.98)
        return self._build_concede(our_price, target_price, step_pct, last_their_price)

    # ---- 议价子构造器（保持 negotiate 主体可读） ----
    def _build_anchor(self, our_price: float, target: float) -> NegotiationMove:
        zh = (
            f"您好，我们这次首单计划 1000 件起，目标采购价 ${our_price:.2f}/件。"
            f"如果价格能谈到这个水平，付款方式可以走 30% 定金 + 70% 见提单。"
        )
        en = (
            f"Hi, we're planning a first order of 1000 units at a target price of "
            f"${our_price:.2f}/unit. With this pricing, we can settle 30% deposit + "
            f"70% against B/L copy."
        )
        return NegotiationMove(
            move_type="anchor",
            proposed_price=round(our_price, 2),
            proposed_terms={"moq": 1000, "payment": "T/T 30/70"},
            script_text=f"中：{zh}\n\nEN: {en}",
            rationale=f"Round 1 anchor 在 target_price -{ANCHOR_DISCOUNT_PCT}%，给对方留出让步空间。",
            expected_supplier_reaction="对方多半会回报价 = anchor + 15-25%，开始正式拉锯。",
            bottom_line_distance_pct=round((target - our_price) / target * 100, 2),
        )

    def _build_concede(
        self,
        our_price: float,
        target: float,
        step_pct: float,
        their_price: float | None,
    ) -> NegotiationMove:
        zh = (
            f"我们再让一步到 ${our_price:.2f}/件，但希望您也对应让 {step_pct:.0f}%。"
            f"另外样品费用希望由贵厂承担，量产时从首单货款里扣除。"
        )
        en = (
            f"We'll move up to ${our_price:.2f}/unit, but we'd appreciate a matching "
            f"{step_pct:.0f}% concession from your side. Also we'd like sample cost "
            f"covered by your factory, deductible from the first PO."
        )
        return NegotiationMove(
            move_type="concede",
            proposed_price=round(our_price, 2),
            proposed_terms={"sample_fee_borne_by": "supplier", "step_pct": step_pct},
            script_text=f"中：{zh}\n\nEN: {en}",
            rationale=f"按 mood 让 {step_pct}%，并要求对等让步，避免单边让步被对方吃下。",
            expected_supplier_reaction="对方一般会让 step_pct 的 60-80%。",
            bottom_line_distance_pct=round((target - our_price) / target * 100, 2),
        )

    def _build_trade(self, target: float, their_price: float) -> NegotiationMove:
        # trade 的核心是用条件换价：MOQ 翻倍 / 长期合同 / 提前付款
        proposed = (target + their_price) / 2
        zh = (
            f"我们提个组合方案：${proposed:.2f}/件，但 MOQ 提到 3000 件，签 12 个月"
            f"框架协议，每月不少于 2000 件，首单付 50% 定金。这样您产能也能稳。"
        )
        en = (
            f"How about ${proposed:.2f}/unit, with MOQ raised to 3000 units, a "
            f"12-month framework contract guaranteeing 2000+ units/month, and 50% "
            f"deposit upfront? This stabilizes your production schedule too."
        )
        return NegotiationMove(
            move_type="trade",
            proposed_price=round(proposed, 2),
            proposed_terms={
                "moq": 3000,
                "framework_months": 12,
                "min_monthly_qty": 2000,
                "deposit_pct": 50,
            },
            script_text=f"中：{zh}\n\nEN: {en}",
            rationale="Round 4+ 改用条件换价，避免纯价格拉锯陷入僵局。",
            expected_supplier_reaction="若供应商产能利用率 < 70%，框架合同诱惑很大，多半会接。",
            bottom_line_distance_pct=round((target - proposed) / target * 100, 2),
        )

    def _build_close(self, target: float, their_price: float, gap_pct: float) -> NegotiationMove:
        final_price = (target + their_price) / 2
        zh = (
            f"OK，我们就 ${final_price:.2f}/件成交，麻烦今天发 PI 给我，我下午"
            f"安排打款。期待长期合作。"
        )
        en = (
            f"Deal at ${final_price:.2f}/unit. Please send the PI today, we'll "
            f"arrange the payment this afternoon. Looking forward to a long-term partnership."
        )
        return NegotiationMove(
            move_type="concede",  # 收口仍标 concede（语义上是最后一让）
            proposed_price=round(final_price, 2),
            proposed_terms={"action": "close_deal", "send_pi": True},
            script_text=f"中：{zh}\n\nEN: {en}",
            rationale=f"双方报价差 {gap_pct:.1f}% < {CLOSE_DEAL_BAND_PCT}%，止损收口，避免节外生枝。",
            expected_supplier_reaction="供应商接受概率 95%+。",
            bottom_line_distance_pct=round((target - final_price) / target * 100, 2),
        )

    def _build_walk_away(self, target: float, their_price: float, distance_pct: float) -> NegotiationMove:
        zh = (
            f"非常感谢您的报价，但 ${their_price:.2f}/件超出我们预算太多（高于目标"
            f" {distance_pct:.0f}%）。我们再观察一下市场，后续如果方案有调整再联系您。"
        )
        en = (
            f"Thanks for your quote, but ${their_price:.2f}/unit is significantly "
            f"above our budget ({distance_pct:.0f}% over target). We'll re-evaluate "
            f"the market and circle back if anything changes."
        )
        return NegotiationMove(
            move_type="walk_away",
            proposed_price=round(target, 2),  # 留下我方目标价作为最后挂单
            proposed_terms={"action": "walk_away", "reason": "over_threshold"},
            script_text=f"中：{zh}\n\nEN: {en}",
            rationale=(
                f"对方报价高于 target_price +{WALK_AWAY_THRESHOLD_PCT}%（实际 "
                f"+{distance_pct:.1f}%），继续谈预期收益已为负，止损退出。"
            ),
            expected_supplier_reaction="部分供应商会在 24-48h 内回头主动让步；不回头说明确实做不到。",
            bottom_line_distance_pct=round(distance_pct, 2),
        )

    # ------------------------------------------------------------------
    # 能力 4：独立站搭建
    # ------------------------------------------------------------------
    async def setup_shopify_store(
        self,
        oauth_token: str,
        theme: str,
        products: list[dict],
    ) -> dict:
        """搭建 Shopify 独立站：选主题 + 批量上架商品。

        :param oauth_token: P4-E Shopify OAuth token。
        :param theme: Shopify 主题 handle（``"dawn"`` / ``"refresh"`` 等）。
        :param products: 待上架商品（轻 schema dict，避免 ProductSpec 强约束）。

        :returns: 包含 ``store_url`` / ``installed_theme`` / ``products_created``。
        """
        if not oauth_token:
            return {
                "ok": False,
                "error": "missing_oauth_token",
                "hint": "请先在「应用授权」完成 Shopify OAuth 连接（P4-E）。",
            }

        # P8 真实接入：调用 P6-D shopify source（admin GraphQL）
        return {
            "ok": True,
            "store_url": "https://demo-store.myshopify.com",
            "installed_theme": theme,
            "products_created": len(products),
            "next_steps": [
                "上传 favicon 与 logo（建议透明 PNG，512x512）",
                "配置 Stripe / PayPal 收款（财税顾问可协助开户）",
                "接入 Google Analytics 4（获客猎手自动化追踪）",
            ],
        }

    # ------------------------------------------------------------------
    # 能力 5：多平台铺货 + 翻译
    # ------------------------------------------------------------------
    async def list_to_platforms(
        self,
        product: ProductSpec,
        platforms: list[str],
        languages: list[str],
    ) -> dict:
        """把一款商品同步上架到多个平台 + 多语言版本。

        :param product: 商品标准化结构。
        :param platforms: 目标平台 ID 列表（``["shopify", "amazon_sp", ...]``）。
        :param languages: 目标语言列表（``["en", "ja", "de"]``）。

        :returns: 每个 (platform, language) 的上架结果汇总。
        """
        # 校验目标平台都在 supported_apps 内
        invalid = [p for p in platforms if p not in self.supported_apps]
        if invalid:
            return {
                "ok": False,
                "error": "unsupported_platforms",
                "invalid": invalid,
                "hint": f"支持的平台：{self.supported_apps}",
            }

        # P8 真实接入：FetchService 路由到 5 个 source.create_product(...)
        # 翻译：调用内容总监 persona 的 multi-language skill。
        results: list[dict] = []
        for platform in platforms:
            for lang in languages:
                title = product.title.get(lang) or product.title.get("en") or product.title.get("zh", product.sku)
                results.append(
                    {
                        "platform": platform,
                        "language": lang,
                        "status": "queued",
                        "preview_title": title,
                    }
                )

        return {
            "ok": True,
            "sku": product.sku,
            "total": len(results),
            "results": results,
            "delegated_to": ["content_director_persona"]  # 多语言文案让内容总监
            if len(languages) > 1
            else [],
        }

    # ------------------------------------------------------------------
    # 能力 6：VAT 合规指引
    # ------------------------------------------------------------------
    async def vat_guidance(self, country: str, scenario: str) -> VATGuidance:
        """给出某国 VAT 申报指引。

        :param country: 国家代码或中文名（``"DE"`` / ``"德国"``）。
        :param scenario: 业务场景描述（``"亚马逊 FBA"`` / ``"独立站直邮"``）。

        :returns: :class:`VATGuidance`，**带强制 disclaimer**。
        """
        # 知识库（迷你版）— P8 接入完整国别 VAT 数据库 + 法规更新订阅
        country_norm = country.strip().upper()
        kb = {
            "DE": (19.0, 10000.0, "monthly", "次月 10 日前"),
            "GERMANY": (19.0, 10000.0, "monthly", "次月 10 日前"),
            "德国": (19.0, 10000.0, "monthly", "次月 10 日前"),
            "UK": (20.0, 0.0, "quarterly", "季后 1 个月零 7 天"),
            "ENGLAND": (20.0, 0.0, "quarterly", "季后 1 个月零 7 天"),
            "英国": (20.0, 0.0, "quarterly", "季后 1 个月零 7 天"),
            "FR": (20.0, 10000.0, "monthly", "次月 19 日前"),
            "FRANCE": (20.0, 10000.0, "monthly", "次月 19 日前"),
            "法国": (20.0, 10000.0, "monthly", "次月 19 日前"),
            "US": (0.0, 0.0, "quarterly", "各州不一，主要看 sales tax nexus"),
            "美国": (0.0, 0.0, "quarterly", "各州不一，主要看 sales tax nexus"),
        }
        rate, threshold, freq, deadline = kb.get(country_norm, (20.0, 10000.0, "quarterly", "请咨询当地税务师"))
        is_us = country_norm in {"US", "USA", "美国"}

        steps: list[str]
        forms: list[str]
        if is_us:
            steps = [
                "判断 nexus 触发的州（仓储 / 销售额 / 雇员所在州）",
                "在触发州申请 sales tax permit",
                "按州周期申报（多数为月报或季报）",
                "保留运单与平台发货报告作为分州销售凭证 7 年",
            ]
            forms = ["State Sales Tax Permit Application", "State Sales Tax Return"]
            registration_required = True
        else:
            steps = [
                "在目的国税务局完成 VAT 注册（建议委托当地税务代表）",
                f"配置 ERP / 平台后台的目的国 VAT 税率（{rate:.1f}%）",
                "保留进口单据 + 销售单据 + 运单 7-10 年（具体年限按国别）",
                f"按 {freq} 频率申报，截止：{deadline}",
                "EORI 号码同步申请（涉及欧盟/英国进口必须）",
            ]
            forms = [
                f"{country} VAT Registration Form",
                f"{country} Periodic VAT Return",
                "Intrastat（欧盟内贸量超阈值时）",
                "EC Sales List（B2B 跨境时）",
            ]
            registration_required = True

        disclaimer = (
            "⚠️ 本指引仅供参考，不构成专业税务或法律意见。VAT/Sales Tax 法规变化频繁，"
            "且不同业务模式（FBA/海外仓/独立站直邮/B2B/B2C）适用规则不同。请务必"
            "委托目的国持牌税务师或律师确认后再行操作；安心智能助手不对依据本指引"
            "产生的税务风险承担责任。"
        )

        return VATGuidance(
            country=country,
            vat_rate_pct=rate,
            threshold_eur=threshold,
            registration_required=registration_required,
            filing_frequency=freq,
            deadline_pattern=deadline,
            recommended_steps=steps,
            forms_to_prepare=forms,
            disclaimer=disclaimer,
        )


__all__ = [
    "EcommerceAssistantAgent",
    "ANCHOR_DISCOUNT_PCT",
    "CONCEDE_STEP_AGGRESSIVE",
    "CONCEDE_STEP_MODERATE",
    "CONCEDE_STEP_FRIENDLY",
    "CLOSE_DEAL_BAND_PCT",
    "WALK_AWAY_THRESHOLD_PCT",
    "TRADE_AFTER_ROUND",
]

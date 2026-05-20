"""DueDiligenceExpertPersona 5 capability 单元测试 (P9-D)。

设计：
    - 不调用真实 LLM / 网络；3 个 specialized agent 全部 mock
    - P6-C 数据源（CreditChinaSource / HistoricalWenshuSource）注入 mock
    - 验证：能力签名 / 风险归一 / forgery 启发式 / 缓存
"""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.agents.personas.dd_models import (
    CreditFlag,
    DueDiligenceReport,
    LitigationRecord,
)
from src.agents.personas.due_diligence_expert import DueDiligenceExpertPersona

# ---------------------------------------------------------------------------
# 工厂：返回带 mock specialized agent + mock P6-C 源的 persona
# ---------------------------------------------------------------------------


def _mock_dd_agent_response(text: str = "尽调结论摘要") -> SimpleNamespace:
    return SimpleNamespace(
        agent_name="due_diligence",
        content=text,
        reasoning="",
        citations=[],
        actions=[],
        metadata={},
    )


def _build_persona(
    *,
    credit_results: list | None = None,
    litigation_results: list | None = None,
    dd_response_text: str = "结构化尽调结论",
) -> DueDiligenceExpertPersona:
    dd_agent = SimpleNamespace(
        process=AsyncMock(return_value=_mock_dd_agent_response(dd_response_text))
    )
    evidence_agent = SimpleNamespace(
        process=AsyncMock(return_value=_mock_dd_agent_response("证据 agent 摘要"))
    )
    sentiment_agent = SimpleNamespace()

    credit_source = SimpleNamespace(search=AsyncMock(return_value=credit_results or []))
    litigation_source = SimpleNamespace(search=AsyncMock(return_value=litigation_results or []))

    return DueDiligenceExpertPersona(
        dd_agent=dd_agent,
        evidence_agent=evidence_agent,
        sentiment_agent=sentiment_agent,
        credit_source=credit_source,
        litigation_source=litigation_source,
    )


def _law_search_result(
    *,
    title: str,
    category: str = "失信被执行人",
    issuing: str = "深圳中院",
    issued: date | None = None,
    role: str | None = None,
    case_type: str = "买卖合同纠纷",
    amount: float | None = None,
):
    """构造 P6-C LawSearchResult mock（dataclass 实例不强求；用 SimpleNamespace 接近）。"""
    extra: dict = {"category": category}
    if role:
        extra["role"] = role
    if case_type:
        extra["case_type"] = case_type
    if amount is not None:
        extra["amount_disputed"] = amount

    return SimpleNamespace(
        source="credit_china",
        law_id=f"id-{abs(hash(title)) % 10_000_000}",
        title=title,
        law_type="case",
        issuing_authority=issuing,
        issued_date=issued or date(2024, 1, 1),
        effective_date=None,
        status="active",
        full_text_url=f"https://example.com/{abs(hash(title)) % 10_000}",
        summary=f"{title} 摘要",
        extra=extra,
    )


# ---------------------------------------------------------------------------
# 1. persona 元信息 + 注册
# ---------------------------------------------------------------------------


def test_persona_metadata_and_registry():
    persona = _build_persona()
    assert persona.persona_id == "due_diligence_expert"
    assert persona.display_name == "尽调专家"
    assert persona.emoji == "🔍"
    assert "company_due_diligence" in persona.capabilities
    assert "evidence_analysis" in persona.capabilities
    assert "relationship_graph" in persona.capabilities
    assert "due_diligence" in persona.backed_by_agents
    assert "evidence_analyst" in persona.backed_by_agents
    assert "sentiment_agent" in persona.backed_by_agents

    # 自动注册
    from src.agents.personas.registry import PersonaRegistry

    reg = PersonaRegistry.instance()
    # 上游 fixture 可能 reset_instance() 清空注册表，但 class 已 import 过、
    # __init_subclass__ 不会再次触发；通过 __subclasses__() 兜底重注册。
    reg._bootstrap_from_subclasses()
    assert reg.has("due_diligence_expert")


# ---------------------------------------------------------------------------
# 2. investigate_company：调通 P6-C 源 + 三档差异
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_investigate_company_quick_skips_litigation():
    persona = _build_persona(
        credit_results=[_law_search_result(title="A 失信被执行人")],
        litigation_results=[_law_search_result(title="L 案", role="defendant", amount=2_000_000)],
    )
    rep = await persona.investigate_company("某公司", "quick")
    # quick 档不查诉讼
    assert rep.litigation_records == []
    # 信用瑕疵仍然查
    assert len(rep.credit_flags) == 1
    assert rep.credit_flags[0].severity == "critical"  # 失信 → critical
    assert rep.investigation_depth == "quick"
    assert rep.report_id.startswith("dd-")


@pytest.mark.asyncio
async def test_investigate_company_standard_includes_litigation():
    persona = _build_persona(
        credit_results=[],
        litigation_results=[
            _law_search_result(title="L 案", role="defendant"),
            _law_search_result(title="L 案 2", role="plaintiff"),
        ],
    )
    rep = await persona.investigate_company("某公司", "standard")
    assert len(rep.litigation_records) == 2
    assert any(r.role == "defendant" for r in rep.litigation_records)
    assert rep.basic_info is not None
    # 引文 = 工商 placeholder + 2 条诉讼
    assert len(rep.citations) >= 3


@pytest.mark.asyncio
async def test_investigate_company_deep_calls_dd_agent():
    persona = _build_persona(dd_response_text="LLM 综合摘要")
    rep = await persona.investigate_company("某公司", "deep")
    assert "LLM 综合摘要" in rep.summary
    persona._dd_agent.process.assert_awaited()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 3. analyze_evidence：forgery + claim 启发式
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_evidence_supports_claim():
    persona = _build_persona()
    text = "本合同已于 2024-01-01 签订，乙方按时履约并支付全部款项。"
    result = await persona.analyze_evidence(text, "乙方按时履约")
    assert result.supports_claim is True
    assert result.confidence > 0
    assert result.supporting_excerpts


@pytest.mark.asyncio
async def test_analyze_evidence_detects_forgery_indicators():
    persona = _build_persona()
    # 多印章描述 + 多日期格式
    text = (
        "本合同甲方公章、乙方公章、监理专用章三方盖章。"
        "签订日期 2024-01-01，备案日期 2024年1月10日，更新日期 24/1/15。"
        "金额 ￥10000 元，大写：壹万圆"
    )
    result = await persona.analyze_evidence(text, "三方已盖章")
    assert "multiple_seal_descriptions" in result.forgery_indicators
    assert "mixed_date_formats" in result.forgery_indicators
    assert result.authenticity_score < 1.0


@pytest.mark.asyncio
async def test_analyze_evidence_rejects_empty():
    persona = _build_persona()
    with pytest.raises(ValueError):
        await persona.analyze_evidence("", "")


# ---------------------------------------------------------------------------
# 4. monitor_sentiment：聚合 / 趋势
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_monitor_sentiment_aggregates_sources():
    persona = _build_persona()
    rep = await persona.monitor_sentiment("某公司", ["weibo", "news"], lookback_days=30)
    assert rep.target == "某公司"
    assert "weibo" in rep.by_source
    assert "news" in rep.by_source
    assert rep.volume == sum(s.get("volume", 0) for s in rep.by_source.values())
    assert rep.overall_sentiment in {"positive", "neutral", "negative", "mixed"}
    assert rep.trend in {"improving", "stable", "deteriorating"}


@pytest.mark.asyncio
async def test_monitor_sentiment_validates_lookback():
    persona = _build_persona()
    with pytest.raises(ValueError):
        await persona.monitor_sentiment("公司", ["weibo"], lookback_days=0)
    with pytest.raises(ValueError):
        await persona.monitor_sentiment("公司", ["weibo"], lookback_days=400)


# ---------------------------------------------------------------------------
# 5. grade_risk：等级映射
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grade_risk_clean_report_is_aaa():
    persona = _build_persona()
    rep = DueDiligenceReport(
        target="干净公司",
        target_type="company",
        investigation_depth="standard",
        basic_info=None,
        credit_flags=[],
        litigation_records=[],
        public_news_count=10,
    )
    grade = await persona.grade_risk(rep)
    assert grade.grade == "AAA"
    assert grade.recommended_action == "trust"
    assert grade.score >= 95


@pytest.mark.asyncio
async def test_grade_risk_critical_flag_lowers_grade():
    persona = _build_persona()
    rep = DueDiligenceReport(
        target="问题公司",
        target_type="company",
        investigation_depth="standard",
        basic_info=None,
        credit_flags=[
            CreditFlag(
                flag_type="court_default",
                description="失信被执行人",
                issued_date=date(2024, 1, 1),
                issuing_authority="深圳中院",
                severity="critical",
            ),
            CreditFlag(
                flag_type="administrative_penalty",
                description="行政处罚 50 万",
                issued_date=date(2024, 6, 1),
                issuing_authority="市场监管局",
                severity="high",
            ),
        ],
        litigation_records=[
            LitigationRecord(
                case_number="2024-粤-0001",
                case_type="买卖合同纠纷",
                court="深圳中院",
                role="defendant",
                amount_disputed=5_000_000.0,
            )
        ],
        public_news_count=600,
    )
    grade = await persona.grade_risk(rep)
    assert grade.grade in {"C", "D", "B", "BB"}
    assert grade.recommended_action in {"avoid", "monitor"}
    assert any("court_default" in f for f in grade.red_flags)
    assert any("big_litigation" in f for f in grade.red_flags)


# ---------------------------------------------------------------------------
# 6. 缓存
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_cache_lookup_and_listing():
    persona = _build_persona()
    rep = await persona.investigate_company("缓存公司", "quick")
    found = persona.get_cached_report(rep.report_id)
    assert found is rep
    listed = persona.list_cached_reports()
    assert any(r.report_id == rep.report_id for r in listed)
    listed_filtered = persona.list_cached_reports(target="缓存")
    assert listed_filtered
    listed_after = persona.list_cached_reports(generated_after=datetime.utcnow())
    # generated_at 严格 < utcnow() 因此应该为空
    assert listed_after == []

# -*- coding: utf-8 -*-
"""P7-B: MarketResearcherAgent 4 capability 单测。

不依赖真 LLM / 真 fetch；用 mock callable 注入。
"""

from __future__ import annotations

import json

import pytest

from src.agents.personas.market_researcher import MarketResearcherAgent
from src.agents.personas.research_models import ResearchReport


class _FakeFetchResp:
    def __init__(self, url: str, text: str, ok: bool = True, tier: str = "L1_HTTP"):
        from types import SimpleNamespace

        self.request = SimpleNamespace(url=url)
        self.text = text
        self.ok = ok
        self.tier_used = SimpleNamespace(value=tier)


class _FakeFetchService:
    """最小 mock fetch_service —— 仅实现 ``fetch_batch``。"""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[str] = []

    async def fetch_batch(self, requests, concurrency: int = 5):
        out = []
        for r in requests:
            self.calls.append(r.url)
            text = self.responses.get(r.url, "<html><title>Mock Page</title>some content</html>")
            out.append(_FakeFetchResp(r.url, text))
        return out


def _stub_llm_returning(payload: dict) -> callable:
    """构造一个返回 JSON 字符串的同步 LLM stub。"""

    def _call(system: str, user: str) -> str:  # noqa: ARG001
        return json.dumps(payload, ensure_ascii=False)

    return _call


# ---------------------------------------------------------------------------
# investigate_company
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_investigate_company_returns_report():
    fetch = _FakeFetchService()
    agent = MarketResearcherAgent(
        llm_callable=_stub_llm_returning(
            {"summary": "公司 X 是一家做 LED 的公司", "rationale": "查到 3 个证据", "next_questions": []}
        ),
        fetch_service=fetch,
    )
    report = await agent.investigate_company("X 公司", depth=1)

    assert isinstance(report, ResearchReport)
    assert report.persona_id == "market_researcher"
    assert "X 公司" in report.question
    assert len(report.steps) >= 1
    assert report.suggested_actions  # 应该被填充
    assert "X 公司" in report.suggested_actions[0]


# ---------------------------------------------------------------------------
# monitor_competitors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_monitor_competitors_parallel_runs():
    fetch = _FakeFetchService()
    agent = MarketResearcherAgent(
        llm_callable=_stub_llm_returning(
            {"summary": "竞品监控样本", "rationale": "", "next_questions": []}
        ),
        fetch_service=fetch,
    )
    results = await agent.monitor_competitors(
        ["竞品 A", "竞品 B", "竞品 C"], aspects=["产品", "定价"]
    )
    assert set(results.keys()) == {"竞品 A", "竞品 B", "竞品 C"}
    for name, rep in results.items():
        assert isinstance(rep, ResearchReport)
        assert name in rep.question
        # 每家都至少跑了 1 步
        assert len(rep.steps) >= 1


@pytest.mark.asyncio
async def test_monitor_competitors_empty_list():
    agent = MarketResearcherAgent()
    results = await agent.monitor_competitors([])
    assert results == {}


# ---------------------------------------------------------------------------
# industry_trend_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_industry_trends_returns_4_axes():
    fetch = _FakeFetchService(
        responses={
            "https://www.bing.com/search?q=LED+%E5%B0%81%E8%A3%85+%E6%94%BF%E7%AD%96+%E6%B3%95%E8%A7%84+30+%E5%A4%A9": (
                "<html><title>政策 通知</title>新法规发布</html>"
            ),
        }
    )
    agent = MarketResearcherAgent(
        llm_callable=_stub_llm_returning(
            {"summary": "趋势：政策收紧", "rationale": "", "next_questions": []}
        ),
        fetch_service=fetch,
    )
    bundle = await agent.industry_trend_analysis("LED 封装", lookback_days=30)
    assert bundle["industry"] == "LED 封装"
    assert bundle["lookback_days"] == 30
    assert isinstance(bundle["report"], ResearchReport)
    # 4 维度切片必须存在（即使为空）
    assert set(bundle["axes"].keys()) == {"policy", "tech", "capital", "market"}


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------


def test_normalize_query_dedup():
    a = MarketResearcherAgent._normalize_query("  Hello  WORLD  ")
    b = MarketResearcherAgent._normalize_query("hello world")
    assert a == b


def test_extract_title_from_html():
    html = "<html><head><title>测试 标题</title></head></html>"
    assert MarketResearcherAgent._extract_title(html) == "测试 标题"


def test_extract_title_from_plain_text():
    text = "\n\n  首行 文本  \n更多内容"
    assert MarketResearcherAgent._extract_title(text) == "首行 文本"


def test_classify_citation_axis():
    from src.agents.personas.research_models import Citation

    pol = Citation(source="x", url="http://a.gov.cn/notice", title="政策通知", excerpt="")
    cap = Citation(source="x", url="http://x.com", title="A 公司完成 B 轮融资", excerpt="")
    tech = Citation(source="x", url="http://x.com", title="新技术突破", excerpt="专利")
    mkt = Citation(source="x", url="http://x.com", title="行业销量", excerpt="")
    assert MarketResearcherAgent._classify_citation_axis(pol) == "policy"
    assert MarketResearcherAgent._classify_citation_axis(cap) == "capital"
    assert MarketResearcherAgent._classify_citation_axis(tech) == "tech"
    assert MarketResearcherAgent._classify_citation_axis(mkt) == "market"

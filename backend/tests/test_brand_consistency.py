"""ContentDirector —— 品牌一致性算法的细颗粒度测试。

重点验证：
    1) 违禁词命中 → severity=block + has_blocking=True + overall_score 被压到 0
    2) voice 关键词覆盖率 < 30% → severity=warn
    3) LLM 不可达时退化为纯规则层（不抛异常）
    4) LLM 评分参与综合分加权
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.agents.personas.content_director import ContentDirectorAgent
from src.agents.personas.content_models import BrandProfile


def _strict_brand() -> BrandProfile:
    return BrandProfile(
        brand_id="b",
        name="ACME",
        tagline="精度即承诺",
        primary_color="#000000",
        tone="专业",
        voice=["匠心", "可靠", "精度", "工艺"],
        forbidden_words=["最强", "第一", "包治百病"],
    )


class _LLM:
    def __init__(self, payload: dict[str, Any] | str | None = None, raise_exc: bool = False):
        self.payload = payload
        self.raise_exc = raise_exc
        self.calls = 0

    async def complete(self, prompt: str, system: str | None = None, **_: Any) -> str:
        self.calls += 1
        if self.raise_exc:
            raise RuntimeError("LLM down")
        if isinstance(self.payload, str):
            return self.payload
        return json.dumps(self.payload or {"tone_score": 0.7, "ai_taste_score": 0.7})


# ---------------------------------------------------------------------------
# 违禁词
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forbidden_word_triggers_block_and_zeroes_score():
    agent = ContentDirectorAgent(llm_client=_LLM({"tone_score": 1.0, "ai_taste_score": 1.0}))
    content = "我们是行业最强，精度第一，匠心可靠的工艺。" * 5  # voice 全覆盖
    report = await agent.check_brand_consistency(content, _strict_brand())

    assert report.has_blocking is True
    blocks = [it for it in report.issues if it["severity"] == "block"]
    assert len(blocks) == 2  # "最强" + "第一"
    # 即便 LLM 给满分，规则层 block 把 overall_score 压到 0
    assert report.overall_score == 0.0
    # suggestions 给出可执行的修复方案
    assert any("替换违禁词" in s for s in report.suggestions)


# ---------------------------------------------------------------------------
# voice 覆盖率
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_low_voice_coverage_triggers_warn():
    agent = ContentDirectorAgent(llm_client=_LLM({"tone_score": 0.9, "ai_taste_score": 0.9}))
    # 4 个 voice 关键词，命中 0 个 → 0% < 30% → warn
    content = "今天天气不错，我们出去吃饭吧，顺便聊点别的事情。" * 5
    report = await agent.check_brand_consistency(content, _strict_brand())

    warns = [it for it in report.issues if it["severity"] == "warn" and it["field"] == "voice"]
    assert len(warns) == 1
    assert "0/4" in warns[0]["actual"] or "0%" in warns[0]["actual"]
    # warn 状态：overall ≤ 0.6（规则层封顶 0.6）
    assert report.overall_score <= 0.6


@pytest.mark.asyncio
async def test_high_voice_coverage_no_warn():
    agent = ContentDirectorAgent(llm_client=_LLM({"tone_score": 0.9, "ai_taste_score": 0.9}))
    # 4 个 voice 关键词命中 3 个 → 75% ≥ 30% → 不 warn
    content = "我们用匠心打造可靠的精度装备。" * 8
    report = await agent.check_brand_consistency(content, _strict_brand())

    voice_warns = [it for it in report.issues if it["field"] == "voice"]
    assert voice_warns == []


# ---------------------------------------------------------------------------
# 短文本 → info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_short_content_triggers_info_only():
    agent = ContentDirectorAgent(llm_client=_LLM({"tone_score": 0.95, "ai_taste_score": 0.95}))
    content = "匠心可靠精度工艺。"  # < 80 字
    report = await agent.check_brand_consistency(content, _strict_brand())

    infos = [it for it in report.issues if it["field"] == "length"]
    assert len(infos) == 1
    assert infos[0]["severity"] == "info"
    assert report.has_blocking is False


# ---------------------------------------------------------------------------
# LLM 故障 → 退化纯规则
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_failure_degrades_to_rule_only():
    agent = ContentDirectorAgent(llm_client=_LLM(raise_exc=True))
    content = "匠心可靠精度工艺。" * 20
    report = await agent.check_brand_consistency(content, _strict_brand())

    # 不抛异常
    assert isinstance(report.overall_score, float)
    # 没有违禁词，规则层不 block
    assert report.has_blocking is False


# ---------------------------------------------------------------------------
# LLM extra_issues 被合并
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_extra_issues_are_merged():
    payload = {
        "tone_score": 0.5,
        "ai_taste_score": 0.4,
        "extra_issues": [
            {"field": "tone", "expected": "专业", "actual": "过于活泼", "severity": "warn"},
            {
                "field": "ai_taste",
                "expected": "拟人",
                "actual": "套话浓",
            },  # 缺 severity → 默认 info
        ],
    }
    agent = ContentDirectorAgent(llm_client=_LLM(payload))
    content = "匠心可靠精度工艺，是我们的承诺。" * 10
    report = await agent.check_brand_consistency(content, _strict_brand())

    fields = {it["field"] for it in report.issues}
    assert "tone" in fields
    assert "ai_taste" in fields
    # 缺 severity 的被默认填 info
    ai_taste_issue = next(it for it in report.issues if it["field"] == "ai_taste")
    assert ai_taste_issue["severity"] == "info"


# ---------------------------------------------------------------------------
# 综合：高质量内容 → 高分
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_high_quality_content_high_score():
    payload = {"tone_score": 0.95, "ai_taste_score": 0.95, "extra_issues": []}
    agent = ContentDirectorAgent(llm_client=_LLM(payload))
    content = (
        "ACME 以匠心做产品，可靠的精度让每一台机床都经得起检验，"
        "30 年工艺沉淀，是我们对客户的承诺。"
    ) * 4
    report = await agent.check_brand_consistency(content, _strict_brand())

    assert report.overall_score >= 0.85
    assert report.has_blocking is False

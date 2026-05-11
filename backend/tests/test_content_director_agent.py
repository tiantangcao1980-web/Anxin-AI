# -*- coding: utf-8 -*-
"""ContentDirectorAgent —— 5 capability 单元测试。

不依赖 DB / 路由层；用 mock LLM 客户端注入 agent。
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.agents.personas.content_director import ContentDirectorAgent
from src.agents.personas.content_models import (
    ArticleDraft,
    BrandProfile,
    ConsistencyReport,
    PosterCopy,
    VideoScript,
)


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------


class _ScriptedLLM:
    """按 (prompt 子串 → 返回值) 顺序匹配的 LLM mock。"""

    def __init__(self, responses: list[tuple[str, str]]):
        self.responses = list(responses)
        self.calls: list[str] = []

    async def complete(self, prompt: str, system: str | None = None, **_: Any) -> str:
        self.calls.append(prompt)
        for needle, value in self.responses:
            if needle in prompt:
                return value
        # fallback：返回空 JSON
        return "{}"


def _brand() -> BrandProfile:
    return BrandProfile(
        brand_id="acme-001",
        name="ACME 精密",
        tagline="精度是承诺",
        primary_color="#1E3A8A",
        secondary_colors=["#F59E0B"],
        fonts={"heading": "Inter", "body": "PingFang SC"},
        tone="专业",
        voice=["匠心", "可靠", "精度"],
        forbidden_words=["最强", "第一"],
        target_audience="制造业采购总监",
    )


# ---------------------------------------------------------------------------
# capability 1: 公众号文章
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_wechat_article_returns_three_titles_and_scrubs_forbidden_words():
    llm_payload = {
        "title_options": [
            "ACME 精密：误差 ≤ 5μm 是这样炼成的",
            "为什么注塑老板都在换 ACME",
            "三张图看懂 ACME 新品",
            "多余的标题",
        ],
        "summary": "ACME 新一代精密注塑机发布。",
        "body_markdown": "# 标题\n\n我们就是行业最强，第一名！\n\n以匠心做产品。",
        "suggested_cover": "蓝色背景 + 设备图",
        "suggested_inline_images": ["设备特写", "测试报告截图"],
        "seo_keywords": ["精密注塑", "ACME"],
        "hashtags": ["#精密制造"],
    }
    llm = _ScriptedLLM([("公众号文章", json.dumps(llm_payload, ensure_ascii=False))])
    agent = ContentDirectorAgent(llm_client=llm)

    draft = await agent.draft_wechat_article("精密注塑机发布", _brand(), length=1500)

    assert isinstance(draft, ArticleDraft)
    assert len(draft.title_options) == 3
    # 违禁词被替换
    assert "最强" not in draft.body_markdown
    assert "第一" not in draft.body_markdown
    assert "▢▢" in draft.body_markdown
    # 阅读时长基于字数
    assert draft.estimated_read_time_min >= 1


@pytest.mark.asyncio
async def test_draft_wechat_article_falls_back_when_llm_returns_garbage():
    llm = _ScriptedLLM([("公众号文章", "this is not json at all")])
    agent = ContentDirectorAgent(llm_client=llm)

    draft = await agent.draft_wechat_article("AI 助手", _brand())

    # fallback 给的兜底数据
    assert len(draft.title_options) == 3
    assert "AI 助手" in draft.title_options[0]


# ---------------------------------------------------------------------------
# capability 2: 短视频脚本
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_video_script_clamps_duration_and_parses_scenes():
    payload = {
        "hook": "3 秒抓眼球",
        "scenes": [
            {"scene_no": 1, "duration_sec": 3, "visual": "厂区航拍", "voiceover": "ACME 30 年", "on_screen_text": "ACME", "bgm_mood": "燃"},
            {"scene_no": 2, "duration_sec": 15, "visual": "机床特写", "voiceover": "5 微米精度", "on_screen_text": "≤5μm"},
            {"scene_no": 3, "duration_sec": 12, "visual": "客户握手", "voiceover": "全球 200+ 客户"},
        ],
        "cta": "私信代理咨询",
        "hashtags": ["#精密制造"],
        "bgm_suggestions": ["industrial-rock"],
    }
    raw = json.dumps(payload, ensure_ascii=False)
    llm = _ScriptedLLM([("短视频脚本", raw)])
    agent = ContentDirectorAgent(llm_client=llm)

    # 请求 120 秒，但 tiktok 上限 60，所以应被钳到 60
    script = await agent.generate_video_script("ACME 品牌片", platform="TikTok", duration_sec=120)

    assert isinstance(script, VideoScript)
    assert script.platform == "tiktok"
    assert len(script.scenes) == 3
    assert script.scenes[0].scene_no == 1
    assert script.total_duration_sec == 30  # 3 + 15 + 12


@pytest.mark.asyncio
async def test_generate_video_script_rejects_unknown_platform():
    agent = ContentDirectorAgent(llm_client=_ScriptedLLM([]))
    with pytest.raises(ValueError, match="不支持的视频平台"):
        await agent.generate_video_script("test", platform="vimeo", duration_sec=30)


# ---------------------------------------------------------------------------
# capability 3: 海报
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_poster_copy_per_size_and_falls_back_individually():
    sizes = ["1080x1080", "1080x1920", "1920x1080"]
    valid = json.dumps(
        {
            "headline": "618 大促",
            "sub_headline": "整厂打样 8 折",
            "body": "限时 7 天",
            "cta": "立即咨询",
            "visual_description": "蓝金主色",
            "layout_hint": "右下 CTA",
        },
        ensure_ascii=False,
    )

    class PartialFail(_ScriptedLLM):
        async def complete(self, prompt: str, system: str | None = None, **kw: Any) -> str:
            self.calls.append(prompt)
            if "1080x1920" in prompt:
                raise RuntimeError("simulated LLM timeout")
            return valid

    agent = ContentDirectorAgent(llm_client=PartialFail([]))
    copies = await agent.generate_poster_copy("618 大促", sizes, _brand())

    assert len(copies) == 3
    for c in copies:
        assert isinstance(c, PosterCopy)
    # 失败的尺寸退化到 fallback
    failed = next(c for c in copies if c.size == "1080x1920")
    assert failed.layout_hint == "fallback"
    # 成功的尺寸保留 LLM 输出
    ok = next(c for c in copies if c.size == "1080x1080")
    assert ok.headline == "618 大促"


@pytest.mark.asyncio
async def test_generate_poster_copy_rejects_empty_sizes():
    agent = ContentDirectorAgent(llm_client=_ScriptedLLM([]))
    with pytest.raises(ValueError):
        await agent.generate_poster_copy("活动", [], _brand())


# ---------------------------------------------------------------------------
# capability 4: 品牌一致性
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_brand_consistency_smoke():
    """规则层 + LLM 层联跑（详细分支在 test_brand_consistency.py 里测）。"""
    llm_payload = {"tone_score": 0.8, "ai_taste_score": 0.85, "extra_issues": []}
    llm = _ScriptedLLM([("tone + AI 味道", json.dumps(llm_payload, ensure_ascii=False))])
    agent = ContentDirectorAgent(llm_client=llm)

    content = "ACME 以匠心做精密设备，可靠的精度让每一台机床都经得起检验。" * 3
    report = await agent.check_brand_consistency(content, _brand())

    assert isinstance(report, ConsistencyReport)
    assert 0.0 <= report.overall_score <= 1.0
    assert report.has_blocking is False


# ---------------------------------------------------------------------------
# capability 5: 多语言本地化
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_localize_returns_per_language_and_strips_fences():
    class LangAwareLLM:
        def __init__(self):
            self.calls: list[str] = []

        async def complete(self, prompt: str, system: str | None = None, **_: Any) -> str:
            self.calls.append(prompt)
            if " en（" in prompt or " en (" in prompt or "为 en" in prompt:
                return "```text\nACME Precision: precision is our promise.\n```"
            if "为 ja" in prompt:
                return "ACME 精密：精度は約束です。"
            return ""

    agent = ContentDirectorAgent(llm_client=LangAwareLLM())
    out = await agent.localize(
        "ACME 精密：精度是承诺",
        target_languages=["en", "ja"],
        market_context={"region": "US", "audience": "B2B engineers"},
    )

    assert set(out.keys()) == {"en", "ja"}
    # 围栏被剥掉
    assert "```" not in out["en"]
    assert "ACME" in out["en"]


@pytest.mark.asyncio
async def test_localize_rejects_empty_languages():
    agent = ContentDirectorAgent(llm_client=_ScriptedLLM([]))
    with pytest.raises(ValueError):
        await agent.localize("hello", [], {})


# ---------------------------------------------------------------------------
# manifest（持久化用）
# ---------------------------------------------------------------------------


def test_manifest_exposes_persona_metadata():
    m = ContentDirectorAgent.manifest()
    assert m["persona_id"] == "content_director"
    assert m["display_name"] == "内容总监"
    assert "wechat_article_drafting" in m["capabilities"]
    assert "docx" in m["backed_by_skills"]
    assert "wechat_mp" in m["supported_apps"]

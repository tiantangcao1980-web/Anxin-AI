# -*- coding: utf-8 -*-
"""ContentDirector persona —— 7 个 endpoint 的集成测试。

通过 FastAPI dependency_overrides 注入一个"假 agent"，
避免真的调用 LLM，同时验证：路由参数校验、状态码、payload 形态、品牌档案隔离。
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from src.agents.personas.content_director import ContentDirectorAgent
from src.agents.personas.content_models import (
    ArticleDraft,
    ConsistencyReport,
    PosterCopy,
    VideoScene,
    VideoScript,
)


# ---------------------------------------------------------------------------
# 假 agent —— 不调 LLM，直接给规整的 dataclass
# ---------------------------------------------------------------------------


class _FakeAgent(ContentDirectorAgent):
    def __init__(self, *, fake_block: bool = False, fail_unknown_platform: bool = True):
        super().__init__(llm_client=None)
        self._fake_block = fake_block
        self._fail_unknown_platform = fail_unknown_platform

    async def draft_wechat_article(self, topic, brand, length=1500):
        return ArticleDraft(
            title_options=["A", "B", "C"],
            summary="摘要",
            body_markdown=f"# {topic}\n\n正文内容很多" * 50,
            suggested_cover="封面",
            suggested_inline_images=["图1"],
            estimated_read_time_min=4,
            seo_keywords=["k1"],
            hashtags=["#h1"],
        )

    async def generate_video_script(self, topic, platform, duration_sec):
        platform_norm = (platform or "").strip().lower()
        if self._fail_unknown_platform and platform_norm not in self._PLATFORM_MAX_SEC:
            raise ValueError("不支持的视频平台")
        return VideoScript(
            platform=platform_norm,
            total_duration_sec=duration_sec,
            scenes=[VideoScene(scene_no=1, duration_sec=duration_sec, visual=topic, voiceover=topic)],
            hook="hook",
            cta="cta",
            hashtags=["#h"],
            bgm_suggestions=["bgm"],
        )

    async def generate_poster_copy(self, occasion, sizes, brand):
        if not sizes:
            raise ValueError("sizes 至少一个")
        return [
            PosterCopy(
                size=size,
                headline=occasion,
                sub_headline="sub",
                body="body",
                cta="cta",
                visual_description="vd",
                layout_hint="lh",
            )
            for size in sizes
        ]

    async def check_brand_consistency(self, content, brand):
        if self._fake_block:
            return ConsistencyReport(
                overall_score=0.0,
                issues=[
                    {"field": "forbidden_words", "expected": "", "actual": "命中", "severity": "block"}
                ],
                suggestions=["删除违禁词"],
            )
        return ConsistencyReport(overall_score=0.92, issues=[], suggestions=[])

    async def localize(self, content, target_languages, market_context=None):
        if not target_languages:
            raise ValueError("target_languages 至少一个")
        return {lang: f"[{lang}] {content}" for lang in target_languages}


@pytest.fixture
def _override_agent():
    """注入 fake agent，返回一个可调节属性的句柄。"""
    from src.api.main import app
    from src.api.routes.persona_content import get_content_director

    state = {"agent": _FakeAgent()}

    def _factory():
        return state["agent"]

    app.dependency_overrides[get_content_director] = _factory
    yield state
    app.dependency_overrides.pop(get_content_director, None)


def _brand_payload() -> dict[str, Any]:
    return {
        "brand_id": "acme",
        "name": "ACME",
        "tagline": "精度即承诺",
        "primary_color": "#1E3A8A",
        "secondary_colors": ["#F59E0B"],
        "fonts": {"heading": "Inter", "body": "PingFang SC"},
        "tone": "专业",
        "voice": ["匠心", "可靠"],
        "forbidden_words": ["最强"],
        "target_audience": "采购总监",
    }


# ---------------------------------------------------------------------------
# endpoint 1: wechat-article
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_wechat_article(auth_client: AsyncClient, _override_agent):
    resp = await auth_client.post(
        "/api/v1/personas/content/wechat-article",
        json={"topic": "新品发布", "brand": _brand_payload(), "length": 1200},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["title_options"]) == 3
    assert body["estimated_read_time_min"] >= 1
    assert "新品发布" in body["body_markdown"]


# ---------------------------------------------------------------------------
# endpoint 2: video-script
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_video_script_ok(auth_client: AsyncClient, _override_agent):
    resp = await auth_client.post(
        "/api/v1/personas/content/video-script",
        json={"topic": "ACME 品牌片", "platform": "tiktok", "duration_sec": 30},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["platform"] == "tiktok"
    assert body["total_duration_sec"] == 30
    assert body["scenes"][0]["scene_no"] == 1


@pytest.mark.asyncio
async def test_post_video_script_unknown_platform_returns_400(auth_client: AsyncClient, _override_agent):
    resp = await auth_client.post(
        "/api/v1/personas/content/video-script",
        json={"topic": "x", "platform": "vimeo", "duration_sec": 30},
    )
    assert resp.status_code == 400
    assert "不支持" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# endpoint 3: poster-copy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_poster_copy(auth_client: AsyncClient, _override_agent):
    resp = await auth_client.post(
        "/api/v1/personas/content/poster-copy",
        json={
            "occasion": "618 大促",
            "sizes": ["1080x1080", "1080x1920"],
            "brand": _brand_payload(),
        },
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 2
    sizes = {it["size"] for it in items}
    assert sizes == {"1080x1080", "1080x1920"}


# ---------------------------------------------------------------------------
# endpoint 4: brand-check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_brand_check_clean(auth_client: AsyncClient, _override_agent):
    resp = await auth_client.post(
        "/api/v1/personas/content/brand-check",
        json={"content": "匠心可靠的产品", "brand": _brand_payload()},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_blocking"] is False
    assert body["requires_human_review"] is False
    assert body["overall_score"] >= 0.0


@pytest.mark.asyncio
async def test_post_brand_check_blocking_requires_human_review(auth_client: AsyncClient, _override_agent):
    _override_agent["agent"] = _FakeAgent(fake_block=True)
    resp = await auth_client.post(
        "/api/v1/personas/content/brand-check",
        json={"content": "我们最强", "brand": _brand_payload()},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_blocking"] is True
    # ⚠️ 合规锁：发布前必须人工 review
    assert body["requires_human_review"] is True


# ---------------------------------------------------------------------------
# endpoint 5: localize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_localize(auth_client: AsyncClient, _override_agent):
    resp = await auth_client.post(
        "/api/v1/personas/content/localize",
        json={
            "content": "精度即承诺",
            "target_languages": ["en", "ja"],
            "market_context": {"region": "US"},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body["translations"].keys()) == {"en", "ja"}
    assert body["translations"]["en"].startswith("[en]")


# ---------------------------------------------------------------------------
# endpoint 6 + 7: brand-profiles GET/POST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_brand_profile_save_and_list(auth_client: AsyncClient, _override_agent):
    # 初始为空
    resp = await auth_client.get("/api/v1/personas/content/brand-profiles")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # 写入
    payload = _brand_payload()
    resp = await auth_client.post("/api/v1/personas/content/brand-profiles", json=payload)
    assert resp.status_code == 200, resp.text
    saved = resp.json()
    assert saved["brand_id"] == "acme"
    assert saved["primary_color"] == "#1E3A8A"

    # 再列
    resp = await auth_client.get("/api/v1/personas/content/brand-profiles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["brand_id"] == "acme"


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(client: AsyncClient, _override_agent):
    """未带 token 的请求应返回 401（依赖 get_current_user_required）。"""
    resp = await client.post(
        "/api/v1/personas/content/wechat-article",
        json={"topic": "x", "brand": _brand_payload(), "length": 800},
    )
    # FastAPI 默认 OAuth2/HTTPBearer 在缺 token 时返回 401 或 403，根据项目实现
    assert resp.status_code in (401, 403)

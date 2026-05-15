"""ContentDirector persona 路由 —— Pydantic schemas。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 品牌档案
# ---------------------------------------------------------------------------


class BrandProfileIn(BaseModel):
    brand_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=64)
    tagline: str = ""
    primary_color: str = "#000000"
    secondary_colors: list[str] = Field(default_factory=list)
    fonts: dict[str, str] = Field(default_factory=dict)
    tone: str = "专业"
    voice: list[str] = Field(default_factory=list)
    forbidden_words: list[str] = Field(default_factory=list)
    target_audience: str = ""


class BrandProfileOut(BrandProfileIn):
    pass


class BrandProfileListOut(BaseModel):
    items: list[BrandProfileOut]
    total: int


# ---------------------------------------------------------------------------
# 公众号文章
# ---------------------------------------------------------------------------


class WechatArticleBody(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    brand: BrandProfileIn
    length: int = Field(default=1500, ge=400, le=8000)


class ArticleDraftOut(BaseModel):
    title_options: list[str]
    summary: str
    body_markdown: str
    suggested_cover: str
    suggested_inline_images: list[str]
    estimated_read_time_min: int
    seo_keywords: list[str]
    hashtags: list[str]


# ---------------------------------------------------------------------------
# 短视频脚本
# ---------------------------------------------------------------------------


class VideoScriptBody(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    platform: str = Field(..., min_length=1)
    duration_sec: int = Field(default=30, ge=5, le=180)


class VideoSceneOut(BaseModel):
    scene_no: int
    duration_sec: int
    visual: str
    voiceover: str
    on_screen_text: str = ""
    bgm_mood: str = ""


class VideoScriptOut(BaseModel):
    platform: str
    total_duration_sec: int
    scenes: list[VideoSceneOut]
    hook: str
    cta: str
    hashtags: list[str]
    bgm_suggestions: list[str]


# ---------------------------------------------------------------------------
# 海报
# ---------------------------------------------------------------------------


class PosterCopyBody(BaseModel):
    occasion: str = Field(..., min_length=1, max_length=100)
    sizes: list[str] = Field(..., min_length=1, max_length=10)
    brand: BrandProfileIn


class PosterCopyOut(BaseModel):
    size: str
    headline: str
    sub_headline: str
    body: str
    cta: str
    visual_description: str
    layout_hint: str = ""


class PosterCopyListOut(BaseModel):
    items: list[PosterCopyOut]


# ---------------------------------------------------------------------------
# 品牌一致性
# ---------------------------------------------------------------------------


class BrandCheckBody(BaseModel):
    content: str = Field(..., min_length=1)
    brand: BrandProfileIn


class ConsistencyReportOut(BaseModel):
    overall_score: float
    issues: list[dict[str, Any]]
    suggestions: list[str]
    has_blocking: bool
    requires_human_review: bool = Field(
        default=False,
        description="发布前是否必须人工 review（公众号等渠道有 block 时强制 True）",
    )


# ---------------------------------------------------------------------------
# 本地化
# ---------------------------------------------------------------------------


class LocalizeBody(BaseModel):
    content: str = Field(..., min_length=1)
    target_languages: list[str] = Field(..., min_length=1, max_length=10)
    market_context: dict[str, Any] = Field(default_factory=dict)


class LocalizeOut(BaseModel):
    translations: dict[str, str]

"""ContentDirector persona —— 数据类。

放在独立模块里，方便：
    1) 路由 schema 直接引用
    2) 单测无需 import agent 主体（避免 LLM 依赖）
    3) 未来 P7-G 框架升级 BasePersonaAgent 时，模型可保持稳定
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 品牌档案
# ---------------------------------------------------------------------------


@dataclass
class BrandProfile:
    """品牌档案 —— 一致性检测、文案生成的"参照系"。"""

    brand_id: str
    name: str
    tagline: str
    primary_color: str  # 形如 "#1E3A8A"
    secondary_colors: list[str] = field(default_factory=list)
    fonts: dict[str, str] = field(
        default_factory=dict
    )  # {"heading": "Inter", "body": "PingFang SC"}
    tone: str = "专业"  # 专业 / 活泼 / 极简 / 温情 / 硬核
    voice: list[str] = field(default_factory=list)  # 用词正向关键词，例："匠心" / "可靠"
    forbidden_words: list[str] = field(default_factory=list)  # 违禁词（绝对不能出现）
    target_audience: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "name": self.name,
            "tagline": self.tagline,
            "primary_color": self.primary_color,
            "secondary_colors": list(self.secondary_colors),
            "fonts": dict(self.fonts),
            "tone": self.tone,
            "voice": list(self.voice),
            "forbidden_words": list(self.forbidden_words),
            "target_audience": self.target_audience,
        }


# ---------------------------------------------------------------------------
# 公众号文章
# ---------------------------------------------------------------------------


@dataclass
class ArticleDraft:
    """公众号文章草稿。

    title_options 给 3 个 SEO 标题候选；body_markdown 是正文 markdown。
    """

    title_options: list[str]
    summary: str
    body_markdown: str
    suggested_cover: str
    suggested_inline_images: list[str] = field(default_factory=list)
    estimated_read_time_min: int = 0
    seo_keywords: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title_options": list(self.title_options),
            "summary": self.summary,
            "body_markdown": self.body_markdown,
            "suggested_cover": self.suggested_cover,
            "suggested_inline_images": list(self.suggested_inline_images),
            "estimated_read_time_min": self.estimated_read_time_min,
            "seo_keywords": list(self.seo_keywords),
            "hashtags": list(self.hashtags),
        }


# ---------------------------------------------------------------------------
# 短视频脚本
# ---------------------------------------------------------------------------


@dataclass
class VideoScene:
    scene_no: int
    duration_sec: int
    visual: str  # 画面描述
    voiceover: str
    on_screen_text: str = ""
    bgm_mood: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_no": self.scene_no,
            "duration_sec": self.duration_sec,
            "visual": self.visual,
            "voiceover": self.voiceover,
            "on_screen_text": self.on_screen_text,
            "bgm_mood": self.bgm_mood,
        }


@dataclass
class VideoScript:
    platform: str  # tiktok / douyin / youtube_shorts / video_account / xiaohongshu
    total_duration_sec: int
    scenes: list[VideoScene]
    hook: str  # 前 3 秒钩子
    cta: str
    hashtags: list[str] = field(default_factory=list)
    bgm_suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "total_duration_sec": self.total_duration_sec,
            "scenes": [s.to_dict() for s in self.scenes],
            "hook": self.hook,
            "cta": self.cta,
            "hashtags": list(self.hashtags),
            "bgm_suggestions": list(self.bgm_suggestions),
        }


# ---------------------------------------------------------------------------
# 海报 / banner 文案
# ---------------------------------------------------------------------------


@dataclass
class PosterCopy:
    size: str  # "1080x1080" / "1080x1920" / "1920x1080" / "750x1334" ...
    headline: str
    sub_headline: str
    body: str
    cta: str
    visual_description: str
    layout_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "headline": self.headline,
            "sub_headline": self.sub_headline,
            "body": self.body,
            "cta": self.cta,
            "visual_description": self.visual_description,
            "layout_hint": self.layout_hint,
        }


# ---------------------------------------------------------------------------
# 品牌一致性
# ---------------------------------------------------------------------------


@dataclass
class ConsistencyReport:
    """品牌一致性检测报告。

    overall_score 取 [0.0, 1.0]，1.0 = 完全合规；
    issues 中每条形如：
        {"field": "tone", "expected": "专业", "actual": "活泼", "severity": "warn"}
    severity ∈ {"info", "warn", "block"}。block 表示发布前必须人工 review。
    """

    overall_score: float
    issues: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def has_blocking(self) -> bool:
        return any(it.get("severity") == "block" for it in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": float(self.overall_score),
            "issues": [dict(it) for it in self.issues],
            "suggestions": list(self.suggestions),
            "has_blocking": self.has_blocking,
        }

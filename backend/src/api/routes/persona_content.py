# -*- coding: utf-8 -*-
"""ContentDirector persona 路由 —— V3 P7-D。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/content"`` 注册）::

    POST   /api/v1/personas/content/wechat-article    生成公众号文章草稿
    POST   /api/v1/personas/content/video-script      生成短视频脚本
    POST   /api/v1/personas/content/poster-copy       生成海报/banner 多尺寸文案
    POST   /api/v1/personas/content/brand-check       品牌一致性检查
    POST   /api/v1/personas/content/localize          多语言本地化
    GET    /api/v1/personas/content/brand-profiles    列已保存品牌档案（按用户隔离）
    POST   /api/v1/personas/content/brand-profiles    保存/更新品牌档案

合规：
    `wechat_article` 返回结果不会自动调用「微信公众号 OAuth 发布」。
    本路由只输出草稿 + ConsistencyReport。前端拿到 `requires_human_review=True`
    时必须强制走人工 review 流程，再走另一条 (P7-E) 发布路由。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.agents.personas.content_director import ContentDirectorAgent
from src.agents.personas.content_models import BrandProfile
from src.api.routes.schemas.persona_content import (
    ArticleDraftOut,
    BrandCheckBody,
    BrandProfileIn,
    BrandProfileListOut,
    BrandProfileOut,
    ConsistencyReportOut,
    LocalizeBody,
    LocalizeOut,
    PosterCopyBody,
    PosterCopyListOut,
    PosterCopyOut,
    VideoScriptBody,
    VideoScriptOut,
    WechatArticleBody,
)
from src.core.deps import get_current_user_required
from src.models.user import User


router = APIRouter()


# ---------------------------------------------------------------------------
# Agent 工厂（便于单测 monkeypatch）
# ---------------------------------------------------------------------------

_agent_factory: Any = None


def get_content_director() -> ContentDirectorAgent:
    """默认工厂：返回一个无 LLM 客户端的 agent（路由层暂时只校验/转发）。

    P7-G 框架升级后，这里会注入真正的 llm_client + skill_runner。当前阶段
    走单测路径时，测试会用 monkeypatch 直接替换 _agent_factory。
    """
    if _agent_factory is not None:
        return _agent_factory()
    # 默认没有 LLM 客户端，路由调用时大部分 capability 会在 _llm() 内部抛错。
    # 这是有意设计：要求上层（P7-G）在路由层注入工厂，而不是默默用 None。
    return ContentDirectorAgent()


# ---------------------------------------------------------------------------
# 简易内存品牌档案存储（按用户隔离）
# 注：这是 P7-D 阶段的占位实现，P7-G/H 接入数据库后会被替换。
# 保留它的好处：单测、Demo、API 联调可以直接跑通。
# ---------------------------------------------------------------------------

_brand_store: dict[str, dict[str, BrandProfileOut]] = {}


def _user_key(user: User) -> str:
    """V3 merge: user.id 可能是 UUID str，改为直接返回 str key。"""
    return str(getattr(user, "id", "") or "")


def _to_profile_dataclass(model: BrandProfileIn) -> BrandProfile:
    return BrandProfile(
        brand_id=model.brand_id,
        name=model.name,
        tagline=model.tagline,
        primary_color=model.primary_color,
        secondary_colors=list(model.secondary_colors),
        fonts=dict(model.fonts),
        tone=model.tone,
        voice=list(model.voice),
        forbidden_words=list(model.forbidden_words),
        target_audience=model.target_audience,
    )


# ---------------------------------------------------------------------------
# capability 1: 公众号文章
# ---------------------------------------------------------------------------


@router.post(
    "/wechat-article",
    response_model=ArticleDraftOut,
    status_code=status.HTTP_200_OK,
    summary="生成公众号文章草稿（不发布）",
)
async def wechat_article(
    body: WechatArticleBody,
    _user: User = Depends(get_current_user_required),
    agent: ContentDirectorAgent = Depends(get_content_director),
) -> ArticleDraftOut:
    try:
        draft = await agent.draft_wechat_article(
            topic=body.topic,
            brand=_to_profile_dataclass(body.brand),
            length=body.length,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ArticleDraftOut(**draft.to_dict())


# ---------------------------------------------------------------------------
# capability 2: 短视频脚本
# ---------------------------------------------------------------------------


@router.post(
    "/video-script",
    response_model=VideoScriptOut,
    status_code=status.HTTP_200_OK,
    summary="生成短视频分镜脚本",
)
async def video_script(
    body: VideoScriptBody,
    _user: User = Depends(get_current_user_required),
    agent: ContentDirectorAgent = Depends(get_content_director),
) -> VideoScriptOut:
    try:
        script = await agent.generate_video_script(
            topic=body.topic,
            platform=body.platform,
            duration_sec=body.duration_sec,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return VideoScriptOut(**script.to_dict())


# ---------------------------------------------------------------------------
# capability 3: 海报
# ---------------------------------------------------------------------------


@router.post(
    "/poster-copy",
    response_model=PosterCopyListOut,
    status_code=status.HTTP_200_OK,
    summary="生成海报 / banner 多尺寸文案",
)
async def poster_copy(
    body: PosterCopyBody,
    _user: User = Depends(get_current_user_required),
    agent: ContentDirectorAgent = Depends(get_content_director),
) -> PosterCopyListOut:
    try:
        copies = await agent.generate_poster_copy(
            occasion=body.occasion,
            sizes=body.sizes,
            brand=_to_profile_dataclass(body.brand),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PosterCopyListOut(items=[PosterCopyOut(**c.to_dict()) for c in copies])


# ---------------------------------------------------------------------------
# capability 4: 品牌一致性
# ---------------------------------------------------------------------------


@router.post(
    "/brand-check",
    response_model=ConsistencyReportOut,
    status_code=status.HTTP_200_OK,
    summary="品牌一致性检查（规则层 + LLM 评分层）",
)
async def brand_check(
    body: BrandCheckBody,
    _user: User = Depends(get_current_user_required),
    agent: ContentDirectorAgent = Depends(get_content_director),
) -> ConsistencyReportOut:
    report = await agent.check_brand_consistency(
        content=body.content,
        brand=_to_profile_dataclass(body.brand),
    )
    payload = report.to_dict()
    payload["requires_human_review"] = bool(report.has_blocking)
    return ConsistencyReportOut(**payload)


# ---------------------------------------------------------------------------
# capability 5: 多语言本地化
# ---------------------------------------------------------------------------


@router.post(
    "/localize",
    response_model=LocalizeOut,
    status_code=status.HTTP_200_OK,
    summary="多语言本地化（含市场语境改写）",
)
async def localize(
    body: LocalizeBody,
    _user: User = Depends(get_current_user_required),
    agent: ContentDirectorAgent = Depends(get_content_director),
) -> LocalizeOut:
    try:
        translations = await agent.localize(
            content=body.content,
            target_languages=body.target_languages,
            market_context=body.market_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LocalizeOut(translations=translations)


# ---------------------------------------------------------------------------
# 品牌档案 CRUD（按用户隔离）
# ---------------------------------------------------------------------------


@router.get(
    "/brand-profiles",
    response_model=BrandProfileListOut,
    status_code=status.HTTP_200_OK,
    summary="列已保存的品牌档案（仅当前用户）",
)
async def list_brand_profiles(
    user: User = Depends(get_current_user_required),
) -> BrandProfileListOut:
    bucket = _brand_store.get(_user_key(user), {})
    items = list(bucket.values())
    return BrandProfileListOut(items=items, total=len(items))


@router.post(
    "/brand-profiles",
    response_model=BrandProfileOut,
    status_code=status.HTTP_200_OK,
    summary="保存或更新品牌档案",
)
async def save_brand_profile(
    body: BrandProfileIn,
    user: User = Depends(get_current_user_required),
) -> BrandProfileOut:
    bucket = _brand_store.setdefault(_user_key(user), {})
    out = BrandProfileOut(**body.model_dump())
    bucket[body.brand_id] = out
    return out

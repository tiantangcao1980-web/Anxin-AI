# -*- coding: utf-8 -*-
"""rag_query 路由 —— P13-C VLM 增强 Query 对外 API。

挂载于 ``/api/v1/rag/query`` (在 ``api/routes/__init__.py`` 中 ``include_router``)::

    POST /api/v1/rag/query/multimodal   完整 multimodal query（默认走 VLM）
    POST /api/v1/rag/query/text-only    仅文本（fallback / no VLM）
    GET  /api/v1/rag/query/health       检查 VLM 可用性

依赖 P13-A (vector + 模态切片) / P13-B (KG) 落地后通过工厂注入；
当前阶段允许使用 stub 实现，便于端到端骨架先跑起来。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from src.api.routes.schemas.rag_query import (
    CitationOut,
    RagQueryHealthOut,
    RagQueryIn,
    RagQueryOut,
    VisualGroundingOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.rag.query import (
    MultimodalQueryRequest,
    MultimodalRetriever,
    VLMQueryEngine,
)


router = APIRouter()


# ===== 工厂 / 依赖注入 =====
#
# 设计原则：本路由对 retriever / engine 不做硬编码；
# 由 ``get_query_engine`` 提供。生产部署时在应用启动时调用
# :func:`set_query_engine` 注入真实实例（P13-A / P13-B 完成后），
# 测试中通过 ``app.dependency_overrides`` 注入 mock。

_query_engine: VLMQueryEngine | None = None


def set_query_engine(engine: VLMQueryEngine | None) -> None:
    """供应用启动 / 测试 setUp 注入引擎单例。"""
    global _query_engine
    _query_engine = engine


def get_query_engine() -> VLMQueryEngine:
    """FastAPI 依赖：返回已注入的 :class:`VLMQueryEngine`。"""
    if _query_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG 多模态查询引擎尚未就绪（P13-A/B 检索骨架未注入）",
        )
    return _query_engine


# ===== endpoints =====


@router.post(
    "/multimodal",
    response_model=RagQueryOut,
    summary="多模态 RAG 查询（VLM 增强）",
)
async def query_multimodal(
    body: RagQueryIn,
    current_user: User = Depends(get_current_user_required),
    engine: VLMQueryEngine = Depends(get_query_engine),
) -> RagQueryOut:
    """完整流程：向量+KG+模态扩展 → 模态加权重排 → VLM 联合作答。"""
    request = _to_request(body, enable_vlm=body.enable_vlm)
    response = await engine.query(request)
    logger.info(
        "rag.query.multimodal user={} top_k={} vlm_used={} duration_ms={}",
        current_user.id,
        body.top_k,
        response.vlm_used,
        response.duration_ms,
    )
    return _to_out(response)


@router.post(
    "/text-only",
    response_model=RagQueryOut,
    summary="多模态 RAG 查询（仅文本，不调 VLM）",
)
async def query_text_only(
    body: RagQueryIn,
    current_user: User = Depends(get_current_user_required),
    engine: VLMQueryEngine = Depends(get_query_engine),
) -> RagQueryOut:
    """仅文本检索路径；忽略 ``enable_vlm`` 强制为 False。"""
    request = _to_request(body, enable_vlm=False)
    response = await engine.query(request)
    logger.info(
        "rag.query.text_only user={} top_k={} duration_ms={}",
        current_user.id,
        body.top_k,
        response.duration_ms,
    )
    return _to_out(response)


@router.get(
    "/health",
    response_model=RagQueryHealthOut,
    summary="检查多模态 query 引擎健康",
)
async def query_health() -> RagQueryHealthOut:
    """暴露检索器组件就绪状态 + VLM vision 能力。无鉴权（与 ``/health`` 风格一致）。"""
    if _query_engine is None:
        return RagQueryHealthOut(
            status="unavailable",
            retriever={},
            vlm_available=False,
            vlm_supports_vision=False,
            notes=["VLMQueryEngine 未注入；P13-A/B 检索器尚未落地"],
        )

    retriever_info: dict[str, Any] = {}
    try:
        retriever_info = _query_engine.retriever.describe()  # type: ignore[union-attr]
    except Exception as exc:  # pragma: no cover - 防御
        logger.warning("retriever.describe 失败: {}", exc)

    vlm_client = _query_engine.vlm_client
    vlm_available = vlm_client is not None
    supports_vision = bool(getattr(vlm_client, "supports_vision", False)) if vlm_client else False

    notes: list[str] = []
    if not vlm_available:
        notes.append("vlm_client 未注入；将走纯文本降级")
    elif not supports_vision:
        notes.append("当前模型不支持 vision；将走纯文本降级")

    return RagQueryHealthOut(
        status="ok" if vlm_available and supports_vision else "degraded",
        retriever=retriever_info,
        vlm_available=vlm_available,
        vlm_supports_vision=supports_vision,
        notes=notes,
    )


# ===== helpers =====


def _to_request(body: RagQueryIn, *, enable_vlm: bool) -> MultimodalQueryRequest:
    return MultimodalQueryRequest(
        query=body.query,
        document_ids=body.document_ids,
        top_k=body.top_k,
        enable_vlm=enable_vlm,
        modality_weights=body.modality_weights,
        language=body.language,
    )


def _to_out(response: Any) -> RagQueryOut:
    return RagQueryOut(
        answer=response.answer,
        citations=[CitationOut(**c) for c in response.citations],
        visual_grounding=[VisualGroundingOut(**vg) for vg in response.visual_grounding],
        confidence=response.confidence,
        duration_ms=response.duration_ms,
        vlm_used=response.vlm_used,
        debug=response.debug or {},
    )

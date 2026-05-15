"""rag_query 路由 Pydantic schemas（P13-C VLM 增强 Query DTO）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ============ 请求 ============


class RagQueryIn(BaseModel):
    """多模态查询请求体。"""

    query: str = Field(..., min_length=1, max_length=2000, description="自然语言问题")
    document_ids: list[str] | None = Field(
        default=None, description="限定检索范围；None 表示全库"
    )
    top_k: int = Field(default=10, ge=1, le=50, description="返回 segment 数上限")
    enable_vlm: bool = Field(default=True, description="是否调用 VLM 联合作答")
    modality_weights: dict[str, float] | None = Field(
        default=None,
        description="覆盖模态权重，例如 {'seal': 1.0, 'image': 0.85}",
    )
    language: str = Field(default="zh-CN", description="回答语言提示")


# ============ 响应 ============


class CitationOut(BaseModel):
    """单条引文。"""

    segment_id: str
    document_id: str
    document_name: str | None = None
    modality: str
    page: int | None = None
    char_range: list[int] | None = None
    snippet: str = ""
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class VisualGroundingOut(BaseModel):
    """VLM "看到" 的图。"""

    segment_id: str
    modality: str | None = None
    document_id: str | None = None
    page: int | None = None


class RagQueryOut(BaseModel):
    """多模态查询响应。"""

    answer: str
    citations: list[CitationOut] = Field(default_factory=list)
    visual_grounding: list[VisualGroundingOut] = Field(default_factory=list)
    confidence: float = 0.0
    duration_ms: int = 0
    vlm_used: bool = False
    debug: dict[str, Any] = Field(default_factory=dict)


# ============ health ============


class RagQueryHealthOut(BaseModel):
    """检索 + VLM 组件健康状态。"""

    status: str  # ok / degraded / unavailable
    retriever: dict[str, Any] = Field(default_factory=dict)
    vlm_available: bool = False
    vlm_supports_vision: bool = False
    notes: list[str] = Field(default_factory=list)

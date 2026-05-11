# -*- coding: utf-8 -*-
"""P13-C VLM 增强 Query - 基础类型。

定义：

- ``Modality`` 枚举（文本 / 图像 / 表格 / 公式 / 公章）
- ``MultimodalQueryRequest`` / ``RetrievedSegment`` / ``VLMQueryResponse`` dataclass
- ``VectorSearcher`` / ``KGBooster`` / ``ModalityExpander`` / ``VLMClient`` Protocol
  这些 Protocol 用 :class:`typing.Protocol` 表达，方便测试 mock，
  且让本模块可以独立运行（不强依赖 P13-A / P13-B）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class Modality(str, Enum):
    """段（segment）的模态。

    与 P13-A 的多模态切片方案保持一致；
    新模态加入时只需扩展枚举与 ``DEFAULT_MODALITY_WEIGHTS``。
    """

    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    FORMULA = "formula"
    SEAL = "seal"  # 公章 / 印鉴

    @classmethod
    def coerce(cls, raw: str | "Modality") -> "Modality":
        """将字符串安全转换为枚举值；未知模态降级为 TEXT。"""
        if isinstance(raw, cls):
            return raw
        try:
            return cls(str(raw).lower())
        except ValueError:
            return cls.TEXT


@dataclass
class MultimodalQueryRequest:
    """多模态查询请求。

    字段：

    - ``query``：自然语言问题
    - ``document_ids``：限定检索范围；None 表示全库
    - ``top_k``：返回 segment 数上限
    - ``enable_vlm``：是否调用 VLM 联合作答（False 走纯文本降级）
    - ``modality_weights``：覆盖默认模态权重（query 级）
    - ``language``：返回回答语言提示（默认中文）
    """

    query: str
    document_ids: list[str] | None = None
    top_k: int = 10
    enable_vlm: bool = True
    modality_weights: dict[str, float] | None = None
    language: str = "zh-CN"


@dataclass
class RetrievedSegment:
    """检索得到的单个段。

    - ``content``：text 模态为字符串；image / seal 模态可为 bytes（base64 前的原图）或 URL 字符串。
    - ``score``：综合得分（vector + bm25 + kg_boost + modality_weight 后）。
    - ``breakdown``：得分明细，便于调试 / 灰度 / 离线评测。
    - ``related_segments``：同章节或 cross_modal 关联的 segment_id。
    """

    segment_id: str
    document_id: str
    modality: Modality
    content: str | bytes
    score: float
    breakdown: dict[str, float] = field(default_factory=dict)
    related_segments: list[str] = field(default_factory=list)
    page: int | None = None
    char_range: tuple[int, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_visual(self) -> bool:
        """段是否需要 VLM 看图（image / seal）。"""
        return self.modality in (Modality.IMAGE, Modality.SEAL)


@dataclass
class VLMQueryResponse:
    """多模态查询响应。

    - ``answer``：最终回答文本
    - ``citations``：结构化引文（DeepTutor 风格，可点击跳转）
    - ``visual_grounding``：VLM "看到" 的图（segment_id + 描述）
    - ``confidence``：[0, 1]，由 retrieval 得分 + VLM 置信度综合
    - ``duration_ms``：端到端耗时
    - ``vlm_used``：是否真的调了 VLM（用于灰度 / 计费）
    """

    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    visual_grounding: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    duration_ms: int = 0
    vlm_used: bool = False
    debug: dict[str, Any] = field(default_factory=dict)


# ===== Protocol：抽象上游依赖（P13-A / P13-B / LLMService） =====


@runtime_checkable
class VectorSearcher(Protocol):
    """向量 + BM25 混合检索接口（由 P13-A 或 现有 chunking_service 实现）。"""

    async def search(
        self,
        *,
        query: str,
        top_k: int,
        document_ids: list[str] | None,
    ) -> list[RetrievedSegment]:
        ...


@runtime_checkable
class KGBooster(Protocol):
    """KG 实体命中加 boost（由 P13-B 实现）。

    输入候选段，返回每个 ``segment_id`` 的 boost 值（可正可负，通常 [0, 0.5]）。
    """

    async def boost(
        self,
        *,
        query: str,
        segments: list[RetrievedSegment],
    ) -> dict[str, float]:
        ...


@runtime_checkable
class ModalityExpander(Protocol):
    """模态扩展（由 P13-A 的 cross_modal 关系实现）。

    给定 text 段，返回同章节 / cross_modal linked 的 image / table / seal 段。
    """

    async def expand(
        self,
        *,
        segments: list[RetrievedSegment],
    ) -> list[RetrievedSegment]:
        ...


@runtime_checkable
class VLMClient(Protocol):
    """VLM 调用接口（包装 LLMService 或 OpenAI vision 兼容 API）。"""

    async def chat_with_vision(
        self,
        *,
        system_prompt: str,
        user_text: str,
        images: list[dict[str, Any]],  # [{segment_id, base64, modality, hint}]
        language: str = "zh-CN",
    ) -> dict[str, Any]:
        """返回 ``{answer: str, mentioned_segment_ids: list[str], confidence: float, tokens: int}``。"""
        ...

    @property
    def supports_vision(self) -> bool:
        """模型是否支持 vision；False 时调用方应降级纯文本。"""
        ...

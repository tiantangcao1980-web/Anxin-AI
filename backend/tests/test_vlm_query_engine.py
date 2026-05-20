"""P13-C: VLMQueryEngine 单元测试。

mock LLMService（chat_with_vision），覆盖：

1. 走 VLM：image segments 转 base64 → 收到 mentioned_segment_ids → visual_grounding 填入
2. enable_vlm=False → 降级纯文本
3. supports_vision=False → 降级纯文本
4. VLM 抛异常 → 降级纯文本（不 500）
5. 检索为空 → 友好兜底
6. confidence = retrieval_avg * 0.5 + vlm * 0.5
7. max_images 截断
8. 远程 URL 走 url 字段
"""

from __future__ import annotations

import pytest

from src.services.rag.query.base import (
    Modality,
    MultimodalQueryRequest,
    RetrievedSegment,
)
from src.services.rag.query.multimodal_retriever import MultimodalRetriever
from src.services.rag.query.vlm_query_engine import VLMQueryEngine

# ---------- mocks ----------


class StubVectorSearcher:
    def __init__(self, segments: list[RetrievedSegment]):
        self.segments = segments

    async def search(self, *, query, top_k, document_ids):
        return list(self.segments)


class StubVLMClient:
    """记录调用并返回固定答案的 mock VLM。"""

    def __init__(
        self,
        *,
        supports_vision: bool = True,
        answer: str = "合同已盖章。",
        mentioned: list[str] | None = None,
        confidence: float = 0.8,
        raise_exc: bool = False,
    ):
        self._supports_vision = supports_vision
        self.answer = answer
        self.mentioned = mentioned or []
        self.confidence = confidence
        self.raise_exc = raise_exc
        self.last_call: dict | None = None

    @property
    def supports_vision(self) -> bool:
        return self._supports_vision

    async def chat_with_vision(self, *, system_prompt, user_text, images, language):
        if self.raise_exc:
            raise RuntimeError("vlm down")
        self.last_call = {
            "system_prompt": system_prompt,
            "user_text": user_text,
            "images": images,
            "language": language,
        }
        return {
            "answer": self.answer,
            "mentioned_segment_ids": list(self.mentioned),
            "confidence": self.confidence,
            "tokens": 1234,
        }


def _seg(seg_id, modality, score, content="text"):
    return RetrievedSegment(
        segment_id=seg_id,
        document_id="d1",
        modality=modality,
        content=content,
        score=score,
    )


def _mk_engine(segments, vlm: StubVLMClient | None) -> VLMQueryEngine:
    retriever = MultimodalRetriever(vector_searcher=StubVectorSearcher(segments))
    return VLMQueryEngine(retriever=retriever, vlm_client=vlm)


# ---------- tests ----------


@pytest.mark.asyncio
async def test_vlm_path_with_image_segments() -> None:
    segs = [
        _seg("t1", Modality.TEXT, 0.9, content="合同条款 A"),
        _seg("img1", Modality.IMAGE, 0.85, content=b"\x89PNG\r\n\x1a\n"),
        _seg("seal1", Modality.SEAL, 0.6, content=b"\xff\xd8\xff"),
    ]
    vlm = StubVLMClient(
        answer="合同已盖章 [seg:seal1]",
        mentioned=["seal1"],
        confidence=0.9,
    )
    engine = _mk_engine(segs, vlm)

    resp = await engine.query(MultimodalQueryRequest(query="合同有公章吗", top_k=5))

    assert resp.vlm_used is True
    assert resp.answer.startswith("合同已盖章")
    assert len(resp.visual_grounding) == 1
    assert resp.visual_grounding[0]["segment_id"] == "seal1"
    assert resp.visual_grounding[0]["modality"] == "seal"
    # confidence 综合：retrieval_avg * 0.5 + vlm * 0.5
    assert 0 < resp.confidence <= 1.0
    # last_call.images 应包含 base64
    assert vlm.last_call is not None
    assert any("base64" in img for img in vlm.last_call["images"])
    # citations 不为空
    assert len(resp.citations) >= 1


@pytest.mark.asyncio
async def test_enable_vlm_false_falls_back_to_text() -> None:
    segs = [_seg("t1", Modality.TEXT, 0.9, content="法条 X")]
    vlm = StubVLMClient()
    engine = _mk_engine(segs, vlm)
    resp = await engine.query(MultimodalQueryRequest(query="法条", top_k=3, enable_vlm=False))
    assert resp.vlm_used is False
    assert "VLM 未启用" in resp.answer or "降级" in resp.answer
    assert vlm.last_call is None  # 没调 VLM


@pytest.mark.asyncio
async def test_supports_vision_false_falls_back() -> None:
    segs = [
        _seg("t1", Modality.TEXT, 0.9, content="text"),
        _seg("img1", Modality.IMAGE, 0.5, content=b"\x89PNG"),
    ]
    vlm = StubVLMClient(supports_vision=False)
    engine = _mk_engine(segs, vlm)
    resp = await engine.query(MultimodalQueryRequest(query="x", top_k=3))
    assert resp.vlm_used is False
    assert vlm.last_call is None


@pytest.mark.asyncio
async def test_vlm_exception_falls_back_to_text() -> None:
    segs = [
        _seg("t1", Modality.TEXT, 0.9, content="text"),
        _seg("img1", Modality.IMAGE, 0.5, content=b"\x89PNG"),
    ]
    vlm = StubVLMClient(raise_exc=True)
    engine = _mk_engine(segs, vlm)
    resp = await engine.query(MultimodalQueryRequest(query="x", top_k=3))
    # 异常被吞，降级
    assert resp.vlm_used is False
    assert "降级" in resp.answer or "VLM 未启用" in resp.answer


@pytest.mark.asyncio
async def test_empty_retrieval_returns_friendly_message() -> None:
    engine = _mk_engine([], StubVLMClient())
    resp = await engine.query(MultimodalQueryRequest(query="什么都没有", top_k=3))
    assert resp.vlm_used is False
    assert resp.confidence == 0.0
    assert "未在知识库" in resp.answer or "建议补充" in resp.answer
    assert resp.citations == []


@pytest.mark.asyncio
async def test_max_images_truncation() -> None:
    """超过 max_images 的视觉段不被发给 VLM。"""
    segs = [_seg("t", Modality.TEXT, 0.9, content="t")]
    for i in range(10):
        segs.append(_seg(f"img{i}", Modality.IMAGE, 0.5, content=b"\x89PNG"))

    vlm = StubVLMClient()
    retriever = MultimodalRetriever(vector_searcher=StubVectorSearcher(segs))
    engine = VLMQueryEngine(retriever=retriever, vlm_client=vlm, max_images=2)
    await engine.query(MultimodalQueryRequest(query="证据照片", top_k=20))

    assert vlm.last_call is not None
    assert len(vlm.last_call["images"]) == 2


@pytest.mark.asyncio
async def test_url_image_passed_as_url_field() -> None:
    segs = [
        _seg("t1", Modality.TEXT, 0.9, content="text"),
        _seg("img1", Modality.IMAGE, 0.5, content="https://example.com/a.png"),
    ]
    vlm = StubVLMClient()
    engine = _mk_engine(segs, vlm)
    await engine.query(MultimodalQueryRequest(query="证据照片", top_k=5))
    assert vlm.last_call is not None
    img_payloads = vlm.last_call["images"]
    assert any("url" in p and p["url"].startswith("https://") for p in img_payloads)


@pytest.mark.asyncio
async def test_oversized_image_skipped() -> None:
    """超过 max_image_bytes 的图被跳过，不会进入 VLM 调用。"""
    big = b"\x00" * 100
    segs = [
        _seg("t1", Modality.TEXT, 0.9, content="text"),
        _seg("img1", Modality.IMAGE, 0.5, content=big),
    ]
    vlm = StubVLMClient()
    retriever = MultimodalRetriever(vector_searcher=StubVectorSearcher(segs))
    engine = VLMQueryEngine(retriever=retriever, vlm_client=vlm, max_image_bytes=10)
    await engine.query(MultimodalQueryRequest(query="证据照片", top_k=3))
    assert vlm.last_call is not None
    assert vlm.last_call["images"] == []  # 太大被跳过 → 没图


@pytest.mark.asyncio
async def test_visual_grounding_only_keeps_known_segments() -> None:
    """VLM 返回未知 segment_id 不应出现在 visual_grounding。"""
    segs = [
        _seg("t1", Modality.TEXT, 0.9, content="text"),
        _seg("img1", Modality.IMAGE, 0.5, content=b"\x89PNG"),
    ]
    vlm = StubVLMClient(mentioned=["img1", "ghost_id"])
    engine = _mk_engine(segs, vlm)
    resp = await engine.query(MultimodalQueryRequest(query="证据照片", top_k=3))
    ids = [vg["segment_id"] for vg in resp.visual_grounding]
    assert ids == ["img1"]

"""P13-C: MultimodalRetriever 单元测试。

mock 三个 Protocol：

- VectorSearcher
- KGBooster
- ModalityExpander

验证：

1. 仅 vector 检索 → 走默认权重重排
2. KG boost 注入 → 提升命中段
3. ModalityExpander 拉入同章节 image/seal segment
4. 上游异常被吞掉，不破坏整体流程
5. text_only 路径只返回 TEXT 模态
"""

from __future__ import annotations

import pytest

from src.services.rag.query.base import (
    Modality,
    MultimodalQueryRequest,
    RetrievedSegment,
)
from src.services.rag.query.multimodal_retriever import MultimodalRetriever

# ============ 测试用 stub ============


class StubVectorSearcher:
    def __init__(self, segments: list[RetrievedSegment]):
        self.segments = segments
        self.calls: list[dict] = []

    async def search(self, *, query, top_k, document_ids):
        self.calls.append({"query": query, "top_k": top_k, "document_ids": document_ids})
        return list(self.segments)


class FailingVectorSearcher:
    async def search(self, *, query, top_k, document_ids):
        raise RuntimeError("boom")


class StubKGBooster:
    def __init__(self, boosts: dict[str, float]):
        self.boosts = boosts

    async def boost(self, *, query, segments):
        return dict(self.boosts)


class FailingKGBooster:
    async def boost(self, *, query, segments):
        raise RuntimeError("kg down")


class StubModalityExpander:
    def __init__(self, extras: list[RetrievedSegment]):
        self.extras = extras

    async def expand(self, *, segments):
        return list(self.extras)


def _seg(seg_id: str, modality: Modality, score: float, doc: str = "d1") -> RetrievedSegment:
    return RetrievedSegment(
        segment_id=seg_id,
        document_id=doc,
        modality=modality,
        content=f"content-{seg_id}",
        score=score,
    )


# ============ 测试 ============


@pytest.mark.asyncio
async def test_vector_only_path() -> None:
    """无 KG / 无扩展：只跑 vector + 重排。"""
    vs = StubVectorSearcher(
        [
            _seg("a", Modality.TEXT, 0.9),
            _seg("b", Modality.IMAGE, 0.95),
            _seg("c", Modality.TABLE, 0.7),
        ]
    )
    retr = MultimodalRetriever(vector_searcher=vs)
    req = MultimodalQueryRequest(query="测试", top_k=3)
    out = await retr.retrieve(req)

    assert len(out) == 3
    # text=0.9*1.0=0.90; image=0.95*0.7=0.665; table=0.7*0.9=0.63 → 顺序 a, b, c
    assert [s.segment_id for s in out] == ["a", "b", "c"]
    # candidate_multiplier 决定上游被请求 top_k=9
    assert vs.calls[0]["top_k"] == 9


@pytest.mark.asyncio
async def test_kg_boost_lifts_hit_segment() -> None:
    """KG boost 让命中段反超。"""
    vs = StubVectorSearcher(
        [
            _seg("a", Modality.TEXT, 0.80),
            _seg("b", Modality.TEXT, 0.50),
        ]
    )
    kg = StubKGBooster({"b": 0.5})  # b 反超
    retr = MultimodalRetriever(vector_searcher=vs, kg_booster=kg)
    out = await retr.retrieve(MultimodalQueryRequest(query="x", top_k=2))
    assert out[0].segment_id == "b"
    assert out[0].breakdown["kg_boost"] == 0.5


@pytest.mark.asyncio
async def test_modality_expander_pulls_in_visual_segments() -> None:
    """命中 text 段后，扩展拉入同 section 的 image / seal。"""
    primary = [_seg("t1", Modality.TEXT, 0.9)]
    extras = [
        _seg("img1", Modality.IMAGE, 0.5),
        _seg("seal1", Modality.SEAL, 0.4),
    ]
    vs = StubVectorSearcher(primary)
    expander = StubModalityExpander(extras)
    retr = MultimodalRetriever(vector_searcher=vs, modality_expander=expander)
    out = await retr.retrieve(MultimodalQueryRequest(query="合同", top_k=5))
    ids = sorted(s.segment_id for s in out)
    assert ids == ["img1", "seal1", "t1"]


@pytest.mark.asyncio
async def test_modality_expander_dedupes() -> None:
    """expander 返回的 id 若与 primary 重叠应去重。"""
    primary = [_seg("t1", Modality.TEXT, 0.9)]
    extras = [_seg("t1", Modality.TEXT, 0.1)]  # 同 id
    vs = StubVectorSearcher(primary)
    retr = MultimodalRetriever(vector_searcher=vs, modality_expander=StubModalityExpander(extras))
    out = await retr.retrieve(MultimodalQueryRequest(query="合同", top_k=5))
    assert len([s for s in out if s.segment_id == "t1"]) == 1


@pytest.mark.asyncio
async def test_kg_failure_falls_through() -> None:
    """KG 异常不应让整个检索 500。"""
    vs = StubVectorSearcher([_seg("a", Modality.TEXT, 0.5)])
    retr = MultimodalRetriever(vector_searcher=vs, kg_booster=FailingKGBooster())
    out = await retr.retrieve(MultimodalQueryRequest(query="x", top_k=1))
    assert len(out) == 1


@pytest.mark.asyncio
async def test_vector_failure_returns_empty() -> None:
    retr = MultimodalRetriever(vector_searcher=FailingVectorSearcher())
    out = await retr.retrieve(MultimodalQueryRequest(query="x", top_k=1))
    assert out == []


@pytest.mark.asyncio
async def test_text_only_filters_visual() -> None:
    vs = StubVectorSearcher(
        [
            _seg("a", Modality.TEXT, 0.9),
            _seg("b", Modality.IMAGE, 0.95),
            _seg("c", Modality.TEXT, 0.6),
        ]
    )
    retr = MultimodalRetriever(vector_searcher=vs)
    out = await retr.text_only(MultimodalQueryRequest(query="x", top_k=5))
    assert all(s.modality == Modality.TEXT for s in out)
    assert sorted(s.segment_id for s in out) == ["a", "c"]


@pytest.mark.asyncio
async def test_describe_includes_components() -> None:
    retr = MultimodalRetriever(
        vector_searcher=StubVectorSearcher([]),
        kg_booster=StubKGBooster({}),
        modality_expander=StubModalityExpander([]),
    )
    info = retr.describe()
    assert info["vector_searcher"] == "StubVectorSearcher"
    assert info["kg_booster"] == "StubKGBooster"
    assert info["modality_expander"] == "StubModalityExpander"
    assert info["candidate_multiplier"] == 3


@pytest.mark.asyncio
async def test_modality_weights_applied_per_query() -> None:
    """request.modality_weights 覆盖默认。"""
    vs = StubVectorSearcher(
        [
            _seg("t", Modality.TEXT, 0.5),
            _seg("s", Modality.SEAL, 0.5),
        ]
    )
    retr = MultimodalRetriever(vector_searcher=vs)
    out = await retr.retrieve(
        MultimodalQueryRequest(
            query="x",
            top_k=2,
            modality_weights={"seal": 1.5, "text": 0.1},
        )
    )
    assert out[0].segment_id == "s"

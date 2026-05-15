"""ModalityRouter 单测（P13-A）。

覆盖：
- route 5 种已知 modality + 1 种 unknown
- filter 保序 + 子集
- stats 计数
"""

from __future__ import annotations

import pytest

from src.services.rag.ingest.multimodal import ModalityRouter, ParsedSegment
from src.services.rag.ingest.multimodal.base import Modality


def _seg(idx: int, modality: str) -> ParsedSegment:
    return ParsedSegment(
        segment_id=f"doc:{idx}",
        modality=modality,
        content=f"content-{idx}",
        metadata={"page": 1},
    )


@pytest.fixture
def router() -> ModalityRouter:
    return ModalityRouter()


@pytest.fixture
def mixed_segments() -> list[ParsedSegment]:
    return [
        _seg(0, Modality.TEXT.value),
        _seg(1, Modality.IMAGE.value),
        _seg(2, Modality.TABLE.value),
        _seg(3, Modality.FORMULA.value),
        _seg(4, Modality.SEAL.value),
        _seg(5, "voice"),  # 未知
    ]


def test_route_groups_by_modality(
    router: ModalityRouter, mixed_segments: list[ParsedSegment]
) -> None:
    buckets = router.route(mixed_segments)
    for m in (
        Modality.TEXT.value,
        Modality.IMAGE.value,
        Modality.TABLE.value,
        Modality.FORMULA.value,
        Modality.SEAL.value,
    ):
        assert m in buckets
        assert buckets[m].count == 1
    # 未知 modality 收口到 ``unknown``
    assert "unknown" in buckets
    assert buckets["unknown"].count == 1
    assert buckets["unknown"].metadata["strict"] is False


def test_route_handles_empty(router: ModalityRouter) -> None:
    assert router.route([]) == {}


def test_filter_keeps_order_and_subset(
    router: ModalityRouter, mixed_segments: list[ParsedSegment]
) -> None:
    out = router.filter(
        mixed_segments,
        modalities=[Modality.IMAGE.value, Modality.TABLE.value],
    )
    assert [s.segment_id for s in out] == ["doc:1", "doc:2"]


def test_stats_counts(router: ModalityRouter, mixed_segments: list[ParsedSegment]) -> None:
    stats = router.stats(mixed_segments)
    assert stats[Modality.TEXT.value] == 1
    assert stats["voice"] == 1
    assert sum(stats.values()) == 6


def test_known_modalities_constant_matches_enum() -> None:
    assert ModalityRouter.KNOWN_MODALITIES == frozenset(m.value for m in Modality)


def test_route_multiple_same_modality(router: ModalityRouter) -> None:
    segs = [_seg(i, Modality.TEXT.value) for i in range(5)]
    buckets = router.route(segs)
    assert buckets[Modality.TEXT.value].count == 5
    # 顺序保留
    assert [s.segment_id for s in buckets[Modality.TEXT.value].segments] == [
        f"doc:{i}" for i in range(5)
    ]

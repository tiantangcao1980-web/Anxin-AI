"""SealDetector 单测（P13-A）。

覆盖：
- 空 / 太短 → 空列表
- mock-marker → 命中
- red_ratio 阈值
- 未实现 backend 抛 NotImplementedError
- bbox / confidence / shape / color 字段齐全
"""

from __future__ import annotations

import pytest

from src.services.rag.ingest.multimodal import SealDetector
from src.services.rag.ingest.multimodal.seal_detector import SealCandidate


@pytest.fixture
def detector() -> SealDetector:
    return SealDetector(min_red_ratio=0.05, backend="mock")


@pytest.mark.asyncio
async def test_empty_returns_no_candidate(detector: SealDetector) -> None:
    assert await detector.detect(b"") == []
    assert await detector.detect(b"\x00\x01") == []


@pytest.mark.asyncio
async def test_mock_marker_hits(detector: SealDetector) -> None:
    payload = b"\x89PNG\r\n\x1a\n<mock-seal-bytes>" + b"\x00" * 64
    out = await detector.detect(payload)
    assert len(out) == 1
    cand = out[0]
    assert isinstance(cand, SealCandidate)
    assert cand.color == "red"
    assert cand.shape == "circle"
    assert 0.0 < cand.confidence <= 1.0
    assert cand.bbox == (820, 1280, 1080, 1540)


@pytest.mark.asyncio
async def test_red_ratio_above_threshold_hits(detector: SealDetector) -> None:
    # 全 0xFF → red_ratio = 1.0 → 命中
    payload = b"\xff" * 256
    out = await detector.detect(payload)
    assert len(out) == 1
    assert out[0].confidence > 0.5


@pytest.mark.asyncio
async def test_red_ratio_below_threshold_misses() -> None:
    # 高阈值 + 全 0x00 → 不命中
    detector = SealDetector(min_red_ratio=0.5, backend="mock")
    out = await detector.detect(b"\x00" * 256)
    assert out == []


def test_estimate_red_ratio_zero_for_empty() -> None:
    assert SealDetector.estimate_red_ratio(b"") == 0.0


def test_estimate_red_ratio_high_for_ff() -> None:
    ratio = SealDetector.estimate_red_ratio(b"\xff" * 100)
    assert ratio > 0.5


@pytest.mark.asyncio
async def test_opencv_backend_is_todo() -> None:
    detector = SealDetector(backend="opencv")
    with pytest.raises(NotImplementedError):
        await detector.detect(b"X" * 64)


@pytest.mark.asyncio
async def test_yolo_backend_is_todo() -> None:
    detector = SealDetector(backend="yolo")
    with pytest.raises(NotImplementedError):
        await detector.detect(b"X" * 64)


@pytest.mark.asyncio
async def test_unknown_backend_raises_value_error() -> None:
    detector = SealDetector(backend="bogus")
    with pytest.raises(ValueError):
        await detector.detect(b"X" * 64)

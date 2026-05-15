"""P6-C 北大法宝 — 未配 PKULAW_API_KEY 时返回 mock + log warning。"""

from __future__ import annotations

import logging

import pytest

from src.services.fetch.sources.legal import LawSearchQuery, PkuLawSource


class TestPkuLawMockFallback:
    @pytest.mark.asyncio
    async def test_search_returns_mock_when_no_key(self, caplog: pytest.LogCaptureFixture) -> None:
        # 显式覆盖 api_key 为空，模拟未配置
        src = PkuLawSource(api_key="")
        with caplog.at_level(logging.WARNING):
            results = await src.search(LawSearchQuery(keyword="民法典"))

        assert len(results) >= 1
        first = results[0]
        assert first.source == "pkulaw"
        assert first.law_id.startswith("pkulaw-mock-")
        assert "MOCK" in first.title
        assert first.extra.get("mock") is True

        # 必须打印 warning
        assert any(
            "PKULAW_API_KEY 未配置" in record.message and record.levelno == logging.WARNING
            for record in caplog.records
        ), "应记录 PKULAW_API_KEY 未配置的 warning"

    @pytest.mark.asyncio
    async def test_get_full_text_mock_when_no_key(self, caplog: pytest.LogCaptureFixture) -> None:
        src = PkuLawSource(api_key="")
        with caplog.at_level(logging.WARNING):
            text = await src.get_full_text("any-law-id")
        assert "[MOCK]" in text
        assert "any-law-id" in text

    @pytest.mark.asyncio
    async def test_health_check_false_when_no_key(self) -> None:
        src = PkuLawSource(api_key="")
        assert await src.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_true_when_key_set(self) -> None:
        src = PkuLawSource(api_key="dummy-key")
        assert await src.health_check() is True

# -*- coding: utf-8 -*-
"""P6-C 国家法律法规数据库 — search 解析与合规护栏测试。"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from src.services.fetch.sources.legal import (
    FlkNpcGovSource,
    LawSearchQuery,
)


def _mock_response(payload: dict[str, Any], status: int = 200) -> httpx.Response:
    """构造 httpx 响应对象。"""
    request = httpx.Request("GET", "https://flk.npc.gov.cn/api/")
    return httpx.Response(
        status_code=status,
        request=request,
        content=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
    )


@pytest.fixture
def sample_payload() -> dict:
    return {
        "result": {
            "data": [
                {
                    "id": "NPC-2020-001",
                    "title": "中华人民共和国民法典",
                    "type": "law",
                    "office": "全国人民代表大会",
                    "publish": "2020-05-28",
                    "expiry": "2021-01-01",
                    "status": "现行有效",
                    "summary": "民法典摘要",
                },
                {
                    "id": "NPC-2023-099",
                    "title": "公司法",
                    "type": "law",
                    "office": "全国人民代表大会常务委员会",
                    "publish": "2023-12-29",
                    "expiry": "2024-07-01",
                    "status": "已修订",
                },
            ]
        }
    }


class TestFlkNpcSearch:
    @pytest.mark.asyncio
    async def test_search_parses_results(self, sample_payload: dict) -> None:
        async def _no_rate() -> None:
            return None

        # 跳过 robots 校验，避免真实网络
        with patch(
            "src.services.fetch.sources.legal.flk_npc_gov._check_robots",
            return_value=True,
        ):
            transport = httpx.MockTransport(
                lambda req: _mock_response(sample_payload)
            )
            async with httpx.AsyncClient(transport=transport) as client:
                src = FlkNpcGovSource(client=client, rate_limiter=_no_rate)
                results = await src.search(
                    LawSearchQuery(keyword="民法典", limit=10)
                )

        assert len(results) == 2
        first = results[0]
        assert first.source == "flk_npc_gov"
        assert first.law_id == "NPC-2020-001"
        assert first.title == "中华人民共和国民法典"
        assert first.issuing_authority == "全国人民代表大会"
        assert first.issued_date == date(2020, 5, 28)
        assert first.effective_date == date(2021, 1, 1)
        assert first.status == "active"
        assert "flk.npc.gov.cn/detail2.html" in first.full_text_url

        second = results[1]
        assert second.status == "amended"

    @pytest.mark.asyncio
    async def test_search_robots_rejection_raises_compliance(self) -> None:
        async def _no_rate() -> None:
            return None

        with patch(
            "src.services.fetch.sources.legal.flk_npc_gov._check_robots",
            return_value=False,
        ):
            src = FlkNpcGovSource(rate_limiter=_no_rate)
            from src.services.fetch.sources.legal import ComplianceError

            with pytest.raises(ComplianceError):
                await src.search(LawSearchQuery(keyword="民法典"))

    @pytest.mark.asyncio
    async def test_get_full_text_handles_json_body(self) -> None:
        async def _no_rate() -> None:
            return None

        def _handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                request=req,
                json={"result": {"body": "第一条 ……"}},
                headers={"content-type": "application/json"},
            )

        with patch(
            "src.services.fetch.sources.legal.flk_npc_gov._check_robots",
            return_value=True,
        ):
            transport = httpx.MockTransport(_handler)
            async with httpx.AsyncClient(transport=transport) as client:
                src = FlkNpcGovSource(client=client, rate_limiter=_no_rate)
                body = await src.get_full_text("NPC-2020-001")

        assert body == "第一条 ……"

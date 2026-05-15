"""P6-C 信用中国 — 客户端测试。"""

from __future__ import annotations

import json

import httpx
import pytest

from src.services.fetch.sources.legal import CreditChinaSource, LawSearchQuery
from src.services.fetch.sources.legal.credit_china import is_valid_uscc


class TestUSCCValidator:
    @pytest.mark.parametrize(
        "code,expected",
        [
            ("91110000600001627B", True),  # 18 位合规
            ("9111000060000162", False),  # 长度不够
            ("91110000600001627Z", False),  # Z 不在合法字符集
            ("", False),
            ("a" * 18, False),  # 小写不允许
        ],
    )
    def test_uscc_validation(self, code: str, expected: bool) -> None:
        assert is_valid_uscc(code) is expected


class TestCreditChinaSearch:
    @pytest.mark.asyncio
    async def test_search_by_company_name_parses_records(self) -> None:
        captured: dict[str, dict] = {}

        def _handler(req: httpx.Request) -> httpx.Response:
            payload = json.loads(req.content.decode("utf-8"))
            captured["payload"] = payload
            return httpx.Response(
                200,
                request=req,
                json={
                    "data": {
                        "list": [
                            {
                                "id": "REC-1",
                                "type": "失信",
                                "title": "某公司被列入失信被执行人",
                                "authority": "北京市朝阳区人民法院",
                                "publishDate": "2024-03-15",
                                "summary": "未履行生效法律文书",
                            },
                            {
                                "id": "REC-2",
                                "type": "行政处罚",
                                "title": "罚款 5 万元",
                                "authority": "市监管局",
                                "publishDate": "2025-01-09",
                            },
                        ]
                    }
                },
                headers={"content-type": "application/json"},
            )

        transport = httpx.MockTransport(_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            src = CreditChinaSource(client=client)
            results = await src.search(LawSearchQuery(keyword="某科技有限公司", limit=20))

        # 校验请求 payload 用的是 NAME 模式
        assert captured["payload"]["queryType"] == "NAME"
        assert captured["payload"]["keyword"] == "某科技有限公司"

        assert len(results) == 2
        assert results[0].source == "credit_china"
        assert results[0].title.startswith("[失信]")
        assert results[0].extra["category"] == "失信"
        assert results[1].title.startswith("[行政处罚]")

    @pytest.mark.asyncio
    async def test_search_by_uscc_uses_uscc_query_type(self) -> None:
        captured: dict[str, dict] = {}

        def _handler(req: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(req.content.decode("utf-8"))
            return httpx.Response(
                200,
                request=req,
                json={"data": {"list": []}},
                headers={"content-type": "application/json"},
            )

        transport = httpx.MockTransport(_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            src = CreditChinaSource(client=client)
            results = await src.search(LawSearchQuery(keyword="91110000600001627B"))

        assert captured["payload"]["queryType"] == "USCC"
        assert results == []

    @pytest.mark.asyncio
    async def test_empty_keyword_rejected(self) -> None:
        src = CreditChinaSource()
        with pytest.raises(ValueError):
            # LawSearchQuery 自身已校验 keyword 非空，故构造时即抛
            await src.search(LawSearchQuery(keyword="   "))

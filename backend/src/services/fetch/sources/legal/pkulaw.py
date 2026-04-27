# -*- coding: utf-8 -*-
"""北大法宝（pkulaw.com）商业付费 API 客户端骨架。

- 全部方法实装为 HTTP 调用结构（GET/POST + headers）
- ``credentials`` 从 ``core.config.get_settings()`` 读 ``PKULAW_API_KEY``
- 凭证缺失时：health_check() 返回 False；search/get_full_text 返回 mock 数据并 log warning
- 真实付费 API 调用以注释形式保留，避免误打商业接口
"""

from __future__ import annotations

import logging
from typing import ClassVar, Optional

import httpx

from src.core.config import get_settings

from .base import (
    BaseLegalSource,
    LawSearchQuery,
    LawSearchResult,
    LawStatus,
    LawType,
)

logger = logging.getLogger(__name__)


_MOCK_RESULTS: list[dict] = [
    {
        "law_id": "pkulaw-mock-001",
        "title": "[MOCK] 中华人民共和国民法典",
        "law_type": LawType.LAW.value,
        "issuing_authority": "全国人民代表大会",
        "issued_date": "2020-05-28",
        "effective_date": "2021-01-01",
        "status": LawStatus.ACTIVE.value,
    },
]


class PkuLawSource(BaseLegalSource):
    """北大法宝商业 API 客户端。"""

    source_id: ClassVar[str] = "pkulaw"
    display_name: ClassVar[str] = "北大法宝"
    requires_credentials: ClassVar[bool] = True
    base_host: ClassVar[str] = "api.pkulaw.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 20.0,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.PKULAW_API_KEY
        self._base_url = (base_url or settings.PKULAW_BASE_URL).rstrip("/")
        self._client = client
        self._owned_client = client is None
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._headers(),
            )
        return self._client

    def _headers(self) -> dict[str, str]:
        h = {
            "User-Agent": "AnxinLegal-FetchService/1.0",
            "Accept": "application/json",
        }
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    async def aclose(self) -> None:
        if self._owned_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # ---- BaseLegalSource ----

    async def search(self, query: LawSearchQuery) -> list[LawSearchResult]:
        if not self._api_key:
            logger.warning(
                "pkulaw: PKULAW_API_KEY 未配置，返回 mock 数据。"
                " 生产环境请在 .env 中配置授权密钥。"
            )
            return self._build_mock_results(query)

        url = f"{self._base_url}/laws/search"
        self._ensure_compliant(url)

        # 真实调用结构（保留为活代码骨架，等部署时启用）：
        # client = await self._get_client()
        # resp = await client.post(url, json={
        #     "keyword": query.keyword,
        #     "type": query.law_type,
        #     "jurisdiction": query.jurisdiction,
        #     "dateFrom": query.date_from.isoformat() if query.date_from else None,
        #     "dateTo": query.date_to.isoformat() if query.date_to else None,
        #     "limit": query.limit,
        #     "offset": query.offset,
        # })
        # resp.raise_for_status()
        # return self._parse(resp.json())

        # 当前阶段（未签授权合同）即使配了 key 也走 mock，避免误产生付费请求
        logger.info("pkulaw: search() 当前为 stub 实现，返回 mock 结果")
        return self._build_mock_results(query)

    async def get_full_text(self, law_id: str) -> str:
        if not law_id:
            raise ValueError("law_id 不能为空")
        if not self._api_key:
            logger.warning("pkulaw: PKULAW_API_KEY 未配置，get_full_text 返回 mock 文本")
            return f"[MOCK] {law_id} 全文（PKULAW_API_KEY 未配置）"

        url = f"{self._base_url}/laws/{law_id}"
        self._ensure_compliant(url)
        # 真实调用骨架：
        # client = await self._get_client()
        # resp = await client.get(url)
        # resp.raise_for_status()
        # return resp.json().get("body", "")
        return f"[MOCK] {law_id} 全文（stub 实现）"

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        # 真实场景下调 /ping；stub 阶段直接返回 True 表示"已配置可调"
        return True

    # ---- 内部工具 ----

    def _build_mock_results(self, query: LawSearchQuery) -> list[LawSearchResult]:
        from datetime import datetime as _dt

        out: list[LawSearchResult] = []
        for raw in _MOCK_RESULTS[: max(query.limit, 1)]:
            out.append(
                LawSearchResult(
                    source=self.source_id,
                    law_id=raw["law_id"],
                    title=raw["title"],
                    law_type=raw["law_type"],
                    issuing_authority=raw["issuing_authority"],
                    issued_date=_dt.strptime(raw["issued_date"], "%Y-%m-%d").date(),
                    effective_date=_dt.strptime(raw["effective_date"], "%Y-%m-%d").date(),
                    status=raw["status"],
                    full_text_url=f"https://www.pkulaw.com/chl/{raw['law_id']}.html",
                    summary=f"mock 占位结果 (keyword={query.keyword})",
                    extra={"mock": True},
                )
            )
        return out

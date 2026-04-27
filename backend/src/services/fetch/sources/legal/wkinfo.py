# -*- coding: utf-8 -*-
"""威科先行（wkinfo.com.cn）商业付费 API 客户端骨架。

- 与 PkuLawSource 同模式：未配 ``WKINFO_API_KEY`` 时返回 mock + log warning
- 真实付费调用以注释保留，避免误产生计费请求
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
        "law_id": "wkinfo-mock-001",
        "title": "[MOCK] 公司法（2023 修订）",
        "law_type": LawType.LAW.value,
        "issuing_authority": "全国人民代表大会常务委员会",
        "issued_date": "2023-12-29",
        "effective_date": "2024-07-01",
        "status": LawStatus.ACTIVE.value,
    },
]


class WkInfoSource(BaseLegalSource):
    """威科先行商业 API 客户端。"""

    source_id: ClassVar[str] = "wkinfo"
    display_name: ClassVar[str] = "威科先行"
    requires_credentials: ClassVar[bool] = True
    base_host: ClassVar[str] = "api.wkinfo.com.cn"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 20.0,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.WKINFO_API_KEY
        self._base_url = (base_url or settings.WKINFO_BASE_URL).rstrip("/")
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
            h["X-Api-Key"] = self._api_key  # 威科习惯用 X-Api-Key
        return h

    async def aclose(self) -> None:
        if self._owned_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # ---- BaseLegalSource ----

    async def search(self, query: LawSearchQuery) -> list[LawSearchResult]:
        if not self._api_key:
            logger.warning(
                "wkinfo: WKINFO_API_KEY 未配置，返回 mock 数据。"
                " 生产环境请在 .env 中配置授权密钥。"
            )
            return self._build_mock_results(query)

        url = f"{self._base_url}/search"
        self._ensure_compliant(url)
        # 真实调用骨架：
        # client = await self._get_client()
        # resp = await client.post(url, json={
        #     "query": query.keyword,
        #     "docType": query.law_type,
        #     "jurisdiction": query.jurisdiction,
        #     "from": query.date_from.isoformat() if query.date_from else None,
        #     "to": query.date_to.isoformat() if query.date_to else None,
        #     "page": query.offset // max(query.limit, 1) + 1,
        #     "size": query.limit,
        # })
        # resp.raise_for_status()
        # return self._parse(resp.json())

        logger.info("wkinfo: search() 当前为 stub 实现，返回 mock 结果")
        return self._build_mock_results(query)

    async def get_full_text(self, law_id: str) -> str:
        if not law_id:
            raise ValueError("law_id 不能为空")
        if not self._api_key:
            logger.warning("wkinfo: WKINFO_API_KEY 未配置，get_full_text 返回 mock 文本")
            return f"[MOCK] {law_id} 全文（WKINFO_API_KEY 未配置）"

        url = f"{self._base_url}/document/{law_id}"
        self._ensure_compliant(url)
        # 真实调用骨架：
        # client = await self._get_client()
        # resp = await client.get(url)
        # resp.raise_for_status()
        # return resp.json().get("content", "")
        return f"[MOCK] {law_id} 全文（stub 实现）"

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
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
                    full_text_url=f"https://law.wkinfo.com.cn/document/{raw['law_id']}",
                    summary=f"mock 占位结果 (keyword={query.keyword})",
                    extra={"mock": True},
                )
            )
        return out

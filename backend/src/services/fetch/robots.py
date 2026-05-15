"""
robots.txt 解析与缓存 — 礼貌抓取的最低底线。

设计：
- 标准库 ``urllib.robotparser.RobotFileParser`` 已经足够好（同步解析，远程获取异步包装）
- per-host 缓存 24h，命中即用
- 失败（无 robots.txt / 5xx）默认放行（与 Google / Bing 行为一致）
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from loguru import logger


@dataclass
class _CachedRobots:
    parser: RobotFileParser
    fetched_at: float


class RobotsCache:
    """异步 robots.txt 缓存。"""

    DEFAULT_TTL = 24 * 3600

    def __init__(
        self,
        *,
        user_agent: str = "AnxinFetcher/1.0",
        ttl_seconds: int = DEFAULT_TTL,
        timeout: float = 5.0,
    ) -> None:
        self._user_agent = user_agent
        self._ttl = ttl_seconds
        self._timeout = timeout
        self._cache: dict[str, _CachedRobots] = {}
        self._lock = asyncio.Lock()

    async def can_fetch(self, url: str) -> bool:
        """返回 True 即允许抓取（含失败放行）。"""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return False
        host_key = f"{parsed.scheme}://{parsed.hostname}"
        robots_url = f"{host_key}/robots.txt"

        parser = await self._get_parser(host_key, robots_url)
        if parser is None:
            return True  # 失败放行
        try:
            return parser.can_fetch(self._user_agent, url)
        except Exception:  # noqa: BLE001
            return True

    async def _get_parser(self, host_key: str, robots_url: str) -> RobotFileParser | None:
        async with self._lock:
            entry = self._cache.get(host_key)
            if entry and (time.monotonic() - entry.fetched_at) < self._ttl:
                return entry.parser

        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                resp = await client.get(robots_url)
            if resp.status_code >= 400:
                # 4xx：通常是没有 robots.txt → 放行
                # 5xx：服务器错误 → 也放行（保持礼貌即可）
                logger.debug(f"[robots] {robots_url} → {resp.status_code}, 放行")
                parser.parse([])
            else:
                parser.parse(resp.text.splitlines())
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[robots] 获取失败 {robots_url}: {e}, 放行")
            parser.parse([])

        async with self._lock:
            self._cache[host_key] = _CachedRobots(parser=parser, fetched_at=time.monotonic())
        return parser

    def clear(self) -> None:
        self._cache.clear()

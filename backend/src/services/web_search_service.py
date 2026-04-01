# -*- coding: utf-8 -*-
"""
Web Search Service — 多源网络搜索服务

灵感来源：BettaFish QueryEngine 的多搜索工具集
支持多个搜索引擎后端，提供统一接口。

搜索引擎优先级：
1. Tavily API（专业搜索，支持深度搜索）
2. Bing Search API
3. DuckDuckGo（免费 fallback）
4. 直接网页抓取
"""

import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

import httpx

from src.core.config import settings


class WebSearchService:
    """多源网络搜索统一服务"""

    def __init__(self):
        self._tavily_key = getattr(settings, "TAVILY_API_KEY", None) or ""
        self._bing_key = getattr(settings, "BING_SEARCH_KEY", None) or ""
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",
        time_range: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        统一搜索入口，自动选择可用引擎

        Args:
            query: 搜索查询
            max_results: 最大结果数
            search_depth: "basic" / "deep"
            time_range: 时间范围 "day" / "week" / "month" / "year"

        Returns:
            [{"title": ..., "snippet": ..., "url": ..., "relevance": ...}]
        """
        # 依次尝试各搜索引擎
        for searcher in [
            self._search_tavily,
            self._search_bing,
            self._search_duckduckgo,
        ]:
            try:
                results = await searcher(query, max_results, search_depth, time_range)
                if results:
                    logger.info(f"搜索成功 [{searcher.__name__}]: {query} → {len(results)} 条")
                    return results
            except Exception as e:
                logger.debug(f"搜索引擎 {searcher.__name__} 失败: {e}")
                continue

        logger.warning(f"所有搜索引擎均失败: {query}")
        return []

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """搜索最近新闻"""
        return await self.search(
            query,
            max_results=max_results,
            time_range="week" if days <= 7 else "month",
        )

    async def search_legal(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """法律相关搜索（附加法律域限定词）"""
        legal_query = f"{query} 诉讼 裁判 法律风险"
        return await self.search(legal_query, max_results)

    # ========== 搜索引擎实现 ==========

    async def _search_tavily(
        self,
        query: str,
        max_results: int,
        search_depth: str,
        time_range: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Tavily Search API"""
        if not self._tavily_key:
            return []

        payload: Dict[str, Any] = {
            "api_key": self._tavily_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": True,
            "include_raw_content": False,
        }
        if time_range:
            payload["time_range"] = time_range

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
                "url": item.get("url", ""),
                "relevance": item.get("score", 0.5),
                "source": "tavily",
                "published_date": item.get("published_date", ""),
            })

        # 如果有 Tavily 的 AI 回答，也加入
        answer = data.get("answer")
        if answer:
            results.insert(0, {
                "title": "AI 综合分析",
                "snippet": answer,
                "url": "",
                "relevance": 0.95,
                "source": "tavily_answer",
            })

        return results

    async def _search_bing(
        self,
        query: str,
        max_results: int,
        search_depth: str,
        time_range: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Bing Web Search API"""
        if not self._bing_key:
            return []

        params: Dict[str, Any] = {
            "q": query,
            "count": max_results,
            "mkt": "zh-CN",
            "textDecorations": False,
        }
        if time_range == "day":
            params["freshness"] = "Day"
        elif time_range == "week":
            params["freshness"] = "Week"
        elif time_range == "month":
            params["freshness"] = "Month"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.bing.microsoft.com/v7.0/search",
                params=params,
                headers={"Ocp-Apim-Subscription-Key": self._bing_key},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "title": item.get("name", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("url", ""),
                "relevance": 0.6,
                "source": "bing",
            })
        return results

    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        search_depth: str,
        time_range: Optional[str],
    ) -> List[Dict[str, Any]]:
        """DuckDuckGo 搜索 (免费 fallback)"""
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params=params,
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []

        # Abstract
        abstract = data.get("Abstract")
        if abstract:
            results.append({
                "title": data.get("Heading", query),
                "snippet": abstract,
                "url": data.get("AbstractURL", ""),
                "relevance": 0.7,
                "source": "duckduckgo",
            })

        # RelatedTopics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                    "relevance": 0.5,
                    "source": "duckduckgo",
                })

        return results


# 全局实例
web_search_service = WebSearchService()

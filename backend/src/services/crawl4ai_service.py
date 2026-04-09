# -*- coding: utf-8 -*-
"""
Crawl4AI 适配层 — LLM 友好的网页爬取服务

替代 Playwright + BeautifulSoup 手写爬虫：
- 自动 JS 渲染 + 反检测
- 输出清洁 Markdown（直接可用于 LLM 上下文）
- 结构化数据提取（替代 CSS selector）
- 内置缓存 + 并发控制
- 失败时降级到 Playwright

Crawl4AI 不可用时（未安装/导入失败），自动降级到 httpx + 简单 HTML 解析
"""

import asyncio
import re
from typing import Dict, Any, Optional, List
from loguru import logger

from src.core.config import settings


class Crawl4AIService:
    """Crawl4AI 网页爬取适配层"""

    def __init__(self):
        self._crawler = None
        self._available = False
        self._init_attempted = False
        self._semaphore = asyncio.Semaphore(settings.CRAWL4AI_MAX_CONCURRENT)

    async def _ensure_init(self):
        """延迟初始化 Crawl4AI（首次使用时才加载）"""
        if self._init_attempted:
            return
        self._init_attempted = True

        if not settings.CRAWL4AI_ENABLED:
            logger.info("[Crawl4AI] 已禁用（CRAWL4AI_ENABLED=False）")
            return

        try:
            from crawl4ai import AsyncWebCrawler
            self._crawler = AsyncWebCrawler(verbose=settings.CRAWL4AI_VERBOSE)
            await self._crawler.awarmup()
            self._available = True
            logger.info("[Crawl4AI] 初始化成功，LLM 友好爬取已就绪")
        except ImportError:
            logger.info("[Crawl4AI] 未安装 crawl4ai，降级到 httpx 简单爬取")
        except Exception as e:
            logger.warning(f"[Crawl4AI] 初始化失败: {e}，降级到 httpx")

    @property
    def is_available(self) -> bool:
        return self._available

    async def crawl_url(
        self,
        url: str,
        extract_strategy: str = "auto",
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        爬取单个 URL，返回结构化内容

        Args:
            url: 目标 URL
            extract_strategy: 提取策略 (auto / markdown / structured)
            timeout: 超时秒数

        Returns:
            {
                "title": str,
                "content": str,        # 清洁的 Markdown 文本
                "html": str,           # 原始 HTML（仅在需要时）
                "metadata": dict,
                "links": list,
                "success": bool,
                "error": Optional[str],
                "source": "crawl4ai" | "httpx_fallback",
            }
        """
        await self._ensure_init()
        effective_timeout = timeout or settings.CRAWL4AI_TIMEOUT

        async with self._semaphore:
            if self._available and self._crawler:
                return await self._crawl_with_crawl4ai(url, effective_timeout)
            else:
                return await self._crawl_with_httpx(url, effective_timeout)

    async def _crawl_with_crawl4ai(self, url: str, timeout: int) -> Dict[str, Any]:
        """使用 Crawl4AI 爬取"""
        try:
            from crawl4ai import CrawlerRunConfig, CacheMode

            config = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED if settings.CRAWL4AI_CACHE_ENABLED else CacheMode.DISABLED,
                page_timeout=timeout * 1000,
                wait_until="networkidle",
            )

            result = await asyncio.wait_for(
                self._crawler.arun(url=url, config=config),
                timeout=timeout + 5,
            )

            if result.success:
                return {
                    "title": result.metadata.get("title", "") if result.metadata else "",
                    "content": result.markdown or result.cleaned_html or "",
                    "html": result.html[:5000] if result.html else "",
                    "metadata": result.metadata or {},
                    "links": [
                        {"text": link.get("text", ""), "url": link.get("href", "")}
                        for link in (result.links.get("internal", []) + result.links.get("external", []))[:20]
                    ] if result.links else [],
                    "success": True,
                    "error": None,
                    "source": "crawl4ai",
                }
            else:
                logger.debug(f"[Crawl4AI] 爬取失败: {url}, error={result.error_message}")
                return await self._crawl_with_httpx(url, timeout)

        except asyncio.TimeoutError:
            logger.debug(f"[Crawl4AI] 爬取超时: {url}")
            return await self._crawl_with_httpx(url, timeout)
        except Exception as e:
            logger.debug(f"[Crawl4AI] 爬取异常: {url}, {e}")
            return await self._crawl_with_httpx(url, timeout)

    async def _crawl_with_httpx(self, url: str, timeout: int) -> Dict[str, Any]:
        """httpx 降级爬取（无 JS 渲染）"""
        try:
            import httpx

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)

            if resp.status_code != 200:
                return {
                    "title": "", "content": "", "html": "",
                    "metadata": {}, "links": [],
                    "success": False,
                    "error": f"HTTP {resp.status_code}",
                    "source": "httpx_fallback",
                }

            html = resp.text
            content = self._html_to_markdown(html)
            title = self._extract_title(html)

            return {
                "title": title,
                "content": content,
                "html": html[:5000],
                "metadata": {"url": str(resp.url), "status_code": resp.status_code},
                "links": self._extract_links(html, str(resp.url))[:20],
                "success": True,
                "error": None,
                "source": "httpx_fallback",
            }

        except Exception as e:
            return {
                "title": "", "content": "", "html": "",
                "metadata": {}, "links": [],
                "success": False,
                "error": str(e),
                "source": "httpx_fallback",
            }

    async def crawl_batch(self, urls: List[str], timeout: Optional[int] = None) -> List[Dict]:
        """批量爬取"""
        tasks = [self.crawl_url(url, timeout=timeout) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def extract_structured(
        self,
        url: str,
        schema: Dict[str, str],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        按 schema 提取结构化数据

        Args:
            url: 目标 URL
            schema: 提取模式 {"field_name": "css_selector_or_description"}

        Returns:
            提取的结构化数据
        """
        result = await self.crawl_url(url, timeout=timeout)
        if not result["success"]:
            return {"success": False, "error": result["error"], "data": {}}

        # 如果 Crawl4AI 可用且支持 LLM 提取
        if self._available:
            try:
                from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
                from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

                extraction_config = CrawlerRunConfig(
                    extraction_strategy=JsonCssExtractionStrategy(schema)
                )
                structured_result = await self._crawler.arun(url=url, config=extraction_config)
                if structured_result.success and structured_result.extracted_content:
                    import json
                    data = json.loads(structured_result.extracted_content)
                    return {"success": True, "data": data, "source": "crawl4ai_structured"}
            except Exception as e:
                logger.debug(f"[Crawl4AI] 结构化提取失败: {e}")

        # 降级：从 Markdown 内容中正则提取
        return {"success": True, "data": {"raw_content": result["content"][:3000]}, "source": "regex_fallback"}

    # ===== HTML 解析工具 =====

    def _html_to_markdown(self, html: str) -> str:
        """简单 HTML → Markdown 转换（降级方案）"""
        text = html
        # 移除 script/style
        text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text, flags=re.IGNORECASE)
        # 标题
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text, flags=re.IGNORECASE)
        # 段落和换行
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        # 列表
        text = re.sub(r'<li[^>]*>', '- ', text, flags=re.IGNORECASE)
        # 移除所有其他 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 移除 HTML 实体
        text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return text.strip()

    def _extract_title(self, html: str) -> str:
        """提取页面标题"""
        match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_links(self, html: str, base_url: str) -> List[Dict]:
        """提取页面链接"""
        links = []
        for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE):
            href = match.group(1)
            text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            if href.startswith('http') and text:
                links.append({"text": text[:100], "url": href})
        return links

    async def close(self):
        """关闭 Crawl4AI 资源"""
        if self._crawler:
            try:
                await self._crawler.aclose()
            except Exception:
                pass


# 全局实例
crawl4ai_service = Crawl4AIService()

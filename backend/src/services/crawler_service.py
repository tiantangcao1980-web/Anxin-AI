"""
LIC 抓取引擎服务
实现数据抓取、清洗、向量化入库和图谱增强的闭环
"""

import asyncio
import inspect
import ipaddress
import socket
import time
import urllib.robotparser
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict, cast
from urllib.parse import ParseResult, urlparse

from loguru import logger

try:
    from playwright.async_api import async_playwright

    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False
    logger.warning(
        "playwright 未安装，网页抓取功能不可用。可通过 pip install playwright && playwright install 启用。"
    )

try:
    from bs4 import BeautifulSoup

    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False
    logger.warning("beautifulsoup4 未安装，HTML 解析功能不可用。")

from src.config.crawler import (
    LEGAL_CRAWLER_USER_AGENT,
    clamp_host_interval,
    normalize_legal_whitelist,
)
from src.core.config import settings
from src.core.database import async_session_maker
from src.services.data_cleaner import data_cleaner
from src.services.graph_service import graph_service
from src.services.knowledge_service import KnowledgeService

if TYPE_CHECKING:
    import httpx
    from playwright.async_api import Browser, Playwright
    from sqlalchemy.ext.asyncio import AsyncSession


ProgressCallback = Callable[[str, str, int, str], object | Awaitable[object]]
BROWSER_FETCH_ROUTE_SCOPE = "browser:fetch"


class CrawlComplianceInfo(TypedDict):
    url: str
    host: str
    user_agent: str
    rate_limit_wait_seconds: float
    robots_allowed: bool
    dry_run: bool


class FetchResult(TypedDict, total=False):
    success: bool
    status_code: int | None
    text: str
    url: str
    compliance: CrawlComplianceInfo


def _is_allowed_runtime_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    hostname = parsed.hostname.lower()
    allowed_hosts = normalize_legal_whitelist(settings.LIC_ALLOWED_HOSTS)
    if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(".local"):
        return False
    if allowed_hosts and not any(
        hostname == allowed or hostname.endswith(f".{allowed}") for allowed in allowed_hosts
    ):
        return False

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        try:
            resolved = {item[4][0] for item in socket.getaddrinfo(hostname, None)}
        except socket.gaierror:
            resolved = set()
        for addr in resolved:
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False

    return True


class CrawlerComplianceError(ValueError):
    """Raised when a URL cannot pass crawler compliance gates."""


class CrawlerRouteAuthorizationError(PermissionError):
    """Raised when browser/crawler execution lacks a valid governed route token."""


def _commercial_environment() -> bool:
    return settings.ENVIRONMENT.lower() in {"staging", "production"}


def browser_fetch_route_governance_required() -> bool:
    return bool(settings.BROWSER_FETCH_ROUTE_TOKEN_REQUIRED or _commercial_environment())


class CrawlerTask:
    def __init__(
        self,
        url: str,
        keyword: str,
        task_id: str,
        owner_id: str | None = None,
        callback: ProgressCallback | None = None,
    ) -> None:
        self.id = task_id
        self.url = url
        self.keyword = keyword
        self.owner_id = owner_id
        self.status: str = "pending"  # pending, running, completed, failed
        self.progress: int = 0
        self.message: str = ""
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.callback = callback
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class CrawlerService:
    """法务情报抓取引擎 (LIC)"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    ]

    def __init__(self) -> None:
        self.tasks: dict[str, CrawlerTask] = {}
        self.global_callbacks: list[ProgressCallback] = []
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._host_last_request_at: dict[str, float] = {}
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def add_callback(self, callback: ProgressCallback) -> None:
        self.global_callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback) -> None:
        if callback in self.global_callbacks:
            self.global_callbacks.remove(callback)

    async def _get_browser(self) -> "Browser":
        if not _HAS_PLAYWRIGHT:
            raise RuntimeError(
                "playwright 未安装，无法使用网页抓取功能。请运行: pip install playwright && playwright install"
            )
        if not self._playwright:
            self._playwright = await async_playwright().start()
        if not self._browser:
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    def _normalize_url(self, url: str) -> str:
        if not _is_allowed_runtime_url(url):
            allowed_hosts = ", ".join(normalize_legal_whitelist(settings.LIC_ALLOWED_HOSTS))
            raise CrawlerComplianceError(
                f"抓取 URL 不在法定白名单或不安全: {url} (allowed={allowed_hosts})"
            )
        return url

    def _host_interval_seconds(self, host: str) -> float:
        overrides = getattr(settings, "LIC_HOST_RATE_LIMIT_SECONDS", {}) or {}
        if isinstance(overrides, dict) and host in overrides:
            return clamp_host_interval(overrides[host])
        return clamp_host_interval(getattr(settings, "LIC_DEFAULT_HOST_RATE_LIMIT_SECONDS", None))

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def _wait_for_host_rate_limit(self, host: str) -> float:
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            interval = self._host_interval_seconds(host)
            now = time.monotonic()
            elapsed = now - self._host_last_request_at.get(host, 0.0)
            wait_seconds = max(0.0, interval - elapsed)
            if wait_seconds > 0:
                await self._sleep(wait_seconds)
            self._host_last_request_at[host] = time.monotonic()
            return wait_seconds

    async def _fetch_robots_txt(self, parsed_url: ParseResult) -> str:
        import httpx

        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        headers = {"User-Agent": LEGAL_CRAWLER_USER_AGENT}
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(robots_url, headers=headers)
        if resp.status_code == 404:
            return ""
        resp.raise_for_status()
        return resp.text

    async def _get_robot_parser(self, url: str) -> urllib.robotparser.RobotFileParser:
        parsed = urlparse(url)
        cache_key = f"{parsed.scheme}://{parsed.netloc}"
        if cache_key in self._robots_cache:
            return self._robots_cache[cache_key]

        robot_parser = urllib.robotparser.RobotFileParser()
        robot_parser.set_url(f"{cache_key}/robots.txt")
        robots_text = await self._fetch_robots_txt(parsed)
        robot_parser.parse(robots_text.splitlines())
        self._robots_cache[cache_key] = robot_parser
        return robot_parser

    async def _assert_robots_allowed(self, url: str) -> None:
        robot_parser = await self._get_robot_parser(url)
        if not robot_parser.can_fetch(LEGAL_CRAWLER_USER_AGENT, url):
            raise CrawlerComplianceError(f"robots.txt 禁止抓取: {url}")

    async def _http_get(
        self, url: str, timeout: float, headers: dict[str, str]
    ) -> "httpx.Response":
        import httpx

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp

    async def fetch(
        self,
        url: str,
        timeout: float = 30.0,
        dry_run: bool = False,
        *,
        org_id: str | None = None,
        route_token: str | None = None,
        consumer_id: str | None = None,
        actor_user_id: str | None = None,
        db: "AsyncSession | None" = None,
    ) -> FetchResult:
        """统一合规抓取入口：白名单、robots、合法 UA、host 频控。"""
        safe_url = self._normalize_url(url)
        parsed = urlparse(safe_url)
        host = (parsed.hostname or "").lower()

        await self._authorize_browser_route(
            org_id=org_id,
            route_token=route_token,
            consumer_id=consumer_id,
            actor_user_id=actor_user_id,
            db=db,
        )
        await self._assert_robots_allowed(safe_url)
        wait_seconds = await self._wait_for_host_rate_limit(host)
        headers = {
            "User-Agent": LEGAL_CRAWLER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        compliance: CrawlComplianceInfo = {
            "url": safe_url,
            "host": host,
            "user_agent": LEGAL_CRAWLER_USER_AGENT,
            "rate_limit_wait_seconds": round(wait_seconds, 3),
            "robots_allowed": True,
            "dry_run": dry_run,
        }
        if dry_run:
            return {"success": True, "status_code": None, "text": "", "compliance": compliance}

        response = await self._http_get(safe_url, timeout, headers)
        final_url = str(response.url)
        if not _is_allowed_runtime_url(final_url):
            raise CrawlerComplianceError(f"抓取目标发生不安全重定向: {final_url}")
        return {
            "success": True,
            "status_code": response.status_code,
            "text": response.text,
            "url": final_url,
            "compliance": compliance,
        }

    async def _authorize_browser_route(
        self,
        *,
        org_id: str | None,
        route_token: str | None,
        consumer_id: str | None,
        actor_user_id: str | None,
        db: "AsyncSession | None",
    ) -> None:
        if not browser_fetch_route_governance_required():
            return

        missing = [
            name
            for name, value in {
                "org_id": org_id,
                "consumer_id": consumer_id,
                "route_token": route_token,
                "db": db,
            }.items()
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise CrawlerRouteAuthorizationError(
                "Browser route token required before crawler fetch; missing "
                + ", ".join(sorted(missing))
            )

        from src.services.agent_governance_service import AgentGovernanceService

        assert db is not None
        assert org_id is not None
        decision = await AgentGovernanceService(db).validate_route_token(
            org_id=org_id,
            raw_token=route_token,
            required_scope=BROWSER_FETCH_ROUTE_SCOPE,
            consumer_id=consumer_id,
            actor_user_id=actor_user_id,
            actor_type="agent_worker",
        )
        if not decision.allowed:
            raise CrawlerRouteAuthorizationError(
                f"Browser route token denied before crawler fetch: {decision.reason_code}"
            )

    async def crawl_latest_laws(self) -> dict[str, str | int]:
        """爬取最新法律法规与指导案例 (自进化功能)"""
        # 目标来源：最高人民法院指导性案例、司法要闻等
        sources = [
            {"name": "最高法指导案例", "url": "https://www.court.gov.cn/fabu-gengduo-16.html"},
            {"name": "法律法规更新", "url": "http://www.npc.gov.cn/npc/c30834/gongbao.shtml"},
        ]

        logger.info("启动法律法规自进化爬取任务...")

        for source in sources:
            task_id = str(uuid.uuid4())
            # 这里的关键词是预定义的，代表“最新法规”
            asyncio.create_task(
                self.crawl_and_process(
                    url=source["url"], keyword=f"自进化:{source['name']}", task_id=task_id
                )
            )

        return {"status": "started", "source_count": len(sources)}

    async def _update_progress(
        self, task: CrawlerTask, status: str, progress: int, message: str
    ) -> None:
        task.status = status
        task.progress = progress
        task.message = message
        task.updated_at = datetime.now()

        logger.info(f"Task {task.id} progress: {progress}% - {message}")

        # 通知全局回调
        for callback in self.global_callbacks:
            try:
                callback_result = callback(task.id, status, progress, message)
                if inspect.isawaitable(callback_result):
                    await cast(Awaitable[object], callback_result)
            except Exception as e:
                logger.error(f"Global callback failed for task {task.id}: {e}")

    async def crawl_and_process(
        self,
        url: str,
        keyword: str,
        task_id: str,
        owner_id: str | None = None,
    ) -> None:
        """抓取并处理流程"""
        task = CrawlerTask(url, keyword, task_id, owner_id=owner_id)
        self.tasks[task_id] = task

        try:
            await self._update_progress(task, "starting", 10, f"开始任务: {url}")

            # 1. 抓取数据
            await self._update_progress(task, "crawling", 20, f"正在抓取: {url}")

            fetch_result: FetchResult = await self.fetch(url, timeout=30)
            content = fetch_result["text"]
            await self._update_progress(task, "crawling", 40, "合规抓取成功")

            soup = BeautifulSoup(content, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=" ", strip=True)

            # 调用业务清洗逻辑
            clean_data: dict[str, Any] = await data_cleaner.clean_html(content)

            # 3. 知识增强 - 向量化入库
            await self._update_progress(
                task, "indexing", 70, "正在进行知识增强 (Qdrant & Neo4j)..."
            )

            doc_id = str(uuid.uuid4())
            async with async_session_maker() as db:
                knowledge_service = KnowledgeService(db)
                # 尝试获取或创建一个默认知识库
                kbs, count = await knowledge_service.list_knowledge_bases(page_size=1)
                if count > 0:
                    kb_id = kbs[0].id
                else:
                    kb = await knowledge_service.create_knowledge_base(
                        name="法务情报库",
                        description="自动抓取的法务情报",
                    )
                    kb_id = kb.id

                # 向量化存入 Qdrant
                await knowledge_service.index_document(
                    kb_id=kb_id,
                    title=title or f"抓取情报: {keyword}",
                    content=text,
                    metadata={
                        "url": fetch_result.get("url", url),
                        "keyword": keyword,
                        "crawler": "crawler_service.fetch",
                        "crawler_compliance": fetch_result.get("compliance", {}),
                        **(clean_data or {}),
                    },
                )
                await db.commit()

            # 4. 同步更新 Neo4j 关联节点
            if clean_data:
                graph_service.add_legal_entities(clean_data, doc_id)

            task.result = {
                "title": title,
                "url": fetch_result.get("url", url),
                "doc_id": doc_id,
                "compliance": fetch_result.get("compliance", {}),
            }
            await self._update_progress(task, "completed", 100, "入库完成，图谱已更新")
            logger.info(f"抓取任务完成: {url}, TaskID: {task_id}")

        except Exception as e:
            logger.error(f"抓取任务失败: {e}")
            task.error = str(e)
            await self._update_progress(task, "error", 100, f"任务失败: {str(e)}")

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """获取任务状态 (用于轮询)"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "id": task.id,
            "url": task.url,
            "keyword": task.keyword,
            "owner_id": task.owner_id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }


# 全局单例
crawler_service = CrawlerService()

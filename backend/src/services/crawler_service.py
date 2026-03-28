"""
LIC 抓取引擎服务
实现数据抓取、清洗、向量化入库和图谱增强的闭环
"""

import asyncio
import random
from typing import Dict, Any, Optional, List, Callable
from loguru import logger
import uuid
from datetime import datetime
try:
    from playwright.async_api import async_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False
    logger.warning("playwright 未安装，网页抓取功能不可用。可通过 pip install playwright && playwright install 启用。")

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False
    logger.warning("beautifulsoup4 未安装，HTML 解析功能不可用。")

from src.services.data_cleaner import data_cleaner
from src.services.knowledge_service import KnowledgeService
from src.services.graph_service import graph_service
from src.core.database import async_session_maker as AsyncSessionLocal

class CrawlerTask:
    def __init__(self, url: str, keyword: str, task_id: str, callback: Optional[Callable] = None):
        self.id = task_id
        self.url = url
        self.keyword = keyword
        self.status = "pending" # pending, running, completed, failed
        self.progress = 0
        self.message = ""
        self.result = None
        self.error = None
        self.callback = callback
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

class CrawlerService:
    """法务情报抓取引擎 (LIC)"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
    ]

    def __init__(self):
        self.tasks: Dict[str, CrawlerTask] = {}
        self.global_callbacks: List[Callable] = []
        self._playwright = None
        self._browser = None

    def add_callback(self, callback: Callable):
        self.global_callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        if callback in self.global_callbacks:
            self.global_callbacks.remove(callback)

    async def _get_browser(self):
        if not _HAS_PLAYWRIGHT:
            raise RuntimeError("playwright 未安装，无法使用网页抓取功能。请运行: pip install playwright && playwright install")
        if not self._playwright:
            self._playwright = await async_playwright().start()
        if not self._browser:
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def crawl_latest_laws(self):
        """爬取最新法律法规与指导案例 (自进化功能)"""
        # 目标来源：最高人民法院指导性案例、司法要闻等
        sources = [
            {"name": "最高法指导案例", "url": "https://www.court.gov.cn/fabu-gengduo-16.html"},
            {"name": "法律法规更新", "url": "http://www.npc.gov.cn/npc/c30834/gongbao.shtml"}
        ]
        
        logger.info("启动法律法规自进化爬取任务...")
        
        for source in sources:
            task_id = str(uuid.uuid4())
            # 这里的关键词是预定义的，代表“最新法规”
            asyncio.create_task(self.crawl_and_process(
                url=source["url"], 
                keyword=f"自进化:{source['name']}", 
                task_id=task_id
            ))
            
        return {"status": "started", "source_count": len(sources)}

    async def _update_progress(self, task: CrawlerTask, status: str, progress: int, message: str):
        task.status = status
        task.progress = progress
        task.message = message
        task.updated_at = datetime.now()
        
        logger.info(f"Task {task.id} progress: {progress}% - {message}")
        
        # 通知全局回调
        for callback in self.global_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task.id, status, progress, message)
                else:
                    callback(task.id, status, progress, message)
            except Exception as e:
                logger.error(f"Global callback failed for task {task.id}: {e}")

    async def crawl_and_process(self, url: str, keyword: str, task_id: str):
        """抓取并处理流程"""
        task = CrawlerTask(url, keyword, task_id)
        self.tasks[task_id] = task
        
        try:
            await self._update_progress(task, "starting", 10, f"开始任务: {url}")
            
            # 1. 抓取数据
            await self._update_progress(task, "crawling", 20, f"正在通过 Playwright 抓取: {url}")
            
            browser = await self._get_browser()
            context = await browser.new_context(user_agent=random.choice(self.USER_AGENTS))
            page = await context.new_page()
            
            try:
                # 模拟随机延迟 (反爬)
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                content = await page.content()
                title = await page.title()
                
                await self._update_progress(task, "crawling", 40, "抓取成功，正在解析内容...")
                
                # 2. 清洗数据
                await self._update_progress(task, "cleaning", 50, "正在清洗数据 (BeautifulSoup & Cleaner)...")
                
                soup = BeautifulSoup(content, 'html.parser')
                # 移除脚本和样式
                for script in soup(["script", "style"]):
                    script.extract()
                
                text = soup.get_text(separator=' ', strip=True)
                
                # 调用业务清洗逻辑
                clean_data = await data_cleaner.clean_html(content)
                
                # 3. 知识增强 - 向量化入库
                await self._update_progress(task, "indexing", 70, "正在进行知识增强 (Qdrant & Neo4j)...")
                
                doc_id = str(uuid.uuid4())
                async with AsyncSessionLocal() as db:
                    knowledge_service = KnowledgeService(db)
                    # 尝试获取或创建一个默认知识库
                    kbs, count = await knowledge_service.list_knowledge_bases(page_size=1)
                    if count > 0:
                        kb_id = kbs[0].id
                    else:
                        kb = await knowledge_service.create_knowledge_base(name="法务情报库", description="自动抓取的法务情报")
                        kb_id = kb.id
                    
                    # 向量化存入 Qdrant
                    await knowledge_service.index_document(
                        kb_id=kb_id,
                        title=title or f"抓取情报: {keyword}",
                        content=text,
                        metadata={
                            "url": url,
                            "keyword": keyword,
                            "crawler": "playwright",
                            **(clean_data or {})
                        }
                    )
                    await db.commit()
                
                # 4. 同步更新 Neo4j 关联节点
                if clean_data:
                    graph_service.add_legal_entities(clean_data, doc_id)
                
                task.result = {
                    "title": title,
                    "url": url,
                    "doc_id": doc_id
                }
                await self._update_progress(task, "completed", 100, "入库完成，图谱已更新")
                logger.info(f"抓取任务完成: {url}, TaskID: {task_id}")
                
            finally:
                await context.close()
                
        except Exception as e:
            logger.error(f"抓取任务失败: {e}")
            task.error = str(e)
            await self._update_progress(task, "error", 100, f"任务失败: {str(e)}")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态 (用于轮询)"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "url": task.url,
            "keyword": task.keyword,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        }

# 全局单例
crawler_service = CrawlerService()

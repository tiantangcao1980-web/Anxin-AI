"""
LIC 抓取引擎路由
"""

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger
from pydantic import BaseModel

from src.config.crawler import normalize_legal_whitelist
from src.core.config import settings
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.core.security import verify_token, verify_token_with_blacklist
from src.models.user import User
from src.services.crawler_service import CrawlerTask, crawler_service

router = APIRouter()

class CrawlRequest(BaseModel):
    url: str | None = "https://example.com/legal-case"
    keyword: str
    task_id: str


def _validate_crawl_url(raw_url: str | None) -> str:
    url = (raw_url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="抓取 URL 不能为空")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="仅允许 http/https 公网 URL")

    hostname = parsed.hostname.lower()
    allowed_hosts = normalize_legal_whitelist(settings.LIC_ALLOWED_HOSTS)
    if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(".local"):
        raise HTTPException(status_code=403, detail="禁止抓取本地或内网地址")
    if allowed_hosts and not any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in allowed_hosts):
        raise HTTPException(status_code=403, detail="该域名不在允许抓取列表中")

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status_code=403, detail="禁止抓取内网地址")
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
                raise HTTPException(status_code=403, detail="禁止抓取内网地址") from None

    return url


def _can_access_task(task: dict[str, Any] | None, user: User) -> bool:
    if not task:
        return False
    if user.role in {"super_admin", "admin"}:
        return True
    return str(task.get("owner_id")) == str(user.id)

@router.post("/crawl")
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_required)
) -> dict[str, Any]:
    """启动抓取任务"""
    safe_url = _validate_crawl_url(request.url)
    background_tasks.add_task(
        crawler_service.crawl_and_process,
        url=safe_url,
        keyword=request.keyword,
        task_id=request.task_id,
        owner_id=str(user.id),
    )
    return UnifiedResponse.success(message="任务已启动", data={"task_id": request.task_id})

@router.post("/evolve")
async def trigger_self_evolution(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_required)
) -> dict[str, Any]:
    """手动触发法律法规自进化爬取"""
    result = await crawler_service.crawl_latest_laws()
    return UnifiedResponse.success(data=result, message="自进化爬取任务已启动")

@router.get("/status/{task_id}")
async def get_crawl_status(
    task_id: str,
    user: User = Depends(get_current_user_required)
) -> dict[str, Any]:
    """查询抓取进度"""
    status = crawler_service.get_task_status(task_id)
    if not status:
        return UnifiedResponse.error(code=404, message="任务不存在")
    if not _can_access_task(status, user):
        return UnifiedResponse.error(code=403, message="无权查看该任务")
    return UnifiedResponse.success(data=status)

@router.websocket("/ws/{task_id}")
async def websocket_lic(
    websocket: WebSocket,
    task_id: str,
    token: str | None = None,
) -> None:
    """LIC 抓取进度实时通知"""
    await websocket.accept()

    if not token:
        await websocket.close(code=4001, reason="缺少认证令牌")
        return

    try:
        user_id = await verify_token_with_blacklist(token)
    except Exception:
        user_id = verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="认证失败")
        return

    task = crawler_service.get_task_status(task_id)
    if not task:
        await websocket.close(code=4004, reason="任务不存在")
        return
    if str(task.get("owner_id")) != str(user_id):
        await websocket.close(code=4003, reason="无权访问该任务")
        return

    logger.info(f"LIC WebSocket连接建立: {task_id}, user={user_id}")

    async def progress_callback(
        tid: str,
        status: str,
        progress: int,
        message: str,
    ) -> None:
        if tid == task_id:
            try:
                await websocket.send_json({
                    "type": "lic_progress",
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "task_id": tid
                })
            except Exception as e:
                logger.debug(f"发送进度通知失败 (连接可能已断开): {e}")

    crawler_service.add_callback(progress_callback)

    try:
        # 发送当前状态（如果任务已经在运行）
        if task_id in crawler_service.tasks:
            task_state: CrawlerTask = crawler_service.tasks[task_id]
            await websocket.send_json({
                "type": "lic_progress",
                "status": task_state.status,
                "progress": task_state.progress,
                "message": task_state.message,
                "task_id": task_id
            })

        while True:
            # 保持连接，接收心跳或任何数据
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"LIC WebSocket断开连接: {task_id}")
    finally:
        crawler_service.remove_callback(progress_callback)

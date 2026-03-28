"""
LIC 抓取引擎路由
"""

import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from src.services.crawler_service import crawler_service
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User

router = APIRouter()

class CrawlRequest(BaseModel):
    url: Optional[str] = "https://example.com/legal-case"
    keyword: str
    task_id: str

@router.post("/crawl")
async def start_crawl(
    request: CrawlRequest, 
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_required)
):
    """启动抓取任务"""
    background_tasks.add_task(
        crawler_service.crawl_and_process,
        url=request.url,
        keyword=request.keyword,
        task_id=request.task_id
    )
    return UnifiedResponse.success(message="任务已启动", data={"task_id": request.task_id})

@router.post("/evolve")
async def trigger_self_evolution(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_required)
):
    """手动触发法律法规自进化爬取"""
    result = await crawler_service.crawl_latest_laws()
    return UnifiedResponse.success(data=result, message="自进化爬取任务已启动")

@router.get("/status/{task_id}")
async def get_crawl_status(
    task_id: str,
    user: User = Depends(get_current_user_required)
):
    """查询抓取进度"""
    status = crawler_service.get_task_status(task_id)
    if not status:
        return UnifiedResponse.error(code=404, message="任务不存在")
    return UnifiedResponse.success(data=status)

@router.websocket("/ws/{task_id}")
async def websocket_lic(websocket: WebSocket, task_id: str):
    """LIC 抓取进度实时通知"""
    await websocket.accept()
    logger.info(f"LIC WebSocket连接建立: {task_id}")
    
    async def progress_callback(tid: str, status: str, progress: int, message: str):
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
            task = crawler_service.tasks[task_id]
            await websocket.send_json({
                "type": "lic_progress",
                "status": task["status"],
                "progress": task["progress"],
                "message": task["message"],
                "task_id": task_id
            })
            
        while True:
            # 保持连接，接收心跳或任何数据
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"LIC WebSocket断开连接: {task_id}")
    finally:
        crawler_service.remove_callback(progress_callback)

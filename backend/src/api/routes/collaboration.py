"""协作编辑API路由（包含WebSocket）"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import json
import asyncio
from uuid import uuid4

from src.core.responses import UnifiedResponse
from src.core.database import get_db, async_session_maker
from src.core.deps import get_current_user
from src.models.user import User
from src.models.collaboration import (
    DocumentSession, DocumentCollaborator, DocumentEdit,
    SessionStatus, CollaboratorRole, EditOperation
)
from src.models.document import Document

from src.services.collaboration_service import CollaborationService

router = APIRouter()


# ============ 连接管理器 ============

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # session_id -> {user_id: websocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # session_id -> {user_id: collaborator_info}
        self.collaborators: Dict[str, Dict[str, dict]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        user_info: dict
    ):
        """接受WebSocket连接"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}
            self.collaborators[session_id] = {}
        
        self.active_connections[session_id][user_id] = websocket
        self.collaborators[session_id][user_id] = {
            **user_info,
            "joined_at": datetime.now().isoformat()
        }
        
        logger.info(f"用户 {user_id} 加入协作会话 {session_id}")
    
    def disconnect(self, session_id: str, user_id: str):
        """断开WebSocket连接"""
        if session_id in self.active_connections:
            if user_id in self.active_connections[session_id]:
                del self.active_connections[session_id][user_id]
            if user_id in self.collaborators[session_id]:
                del self.collaborators[session_id][user_id]
            
            # 如果没有活跃连接，清理会话
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                del self.collaborators[session_id]
        
        logger.info(f"用户 {user_id} 离开协作会话 {session_id}")
    
    async def broadcast(
        self,
        session_id: str,
        message: dict,
        exclude_user: Optional[str] = None
    ):
        """广播消息给会话中的所有用户"""
        if session_id not in self.active_connections:
            return
        
        disconnected = []
        for user_id, websocket in self.active_connections[session_id].items():
            if exclude_user and user_id == exclude_user:
                continue
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                disconnected.append(user_id)
        
        # 清理断开的连接
        for user_id in disconnected:
            self.disconnect(session_id, user_id)
    
    async def send_personal(self, session_id: str, user_id: str, message: dict):
        """发送消息给特定用户"""
        if session_id in self.active_connections:
            if user_id in self.active_connections[session_id]:
                try:
                    await self.active_connections[session_id][user_id].send_json(message)
                except Exception as e:
                    logger.error(f"发送消息失败: {e}")
                    self.disconnect(session_id, user_id)
    
    def get_collaborators(self, session_id: str) -> List[dict]:
        """获取会话中的所有协作者"""
        if session_id in self.collaborators:
            return list(self.collaborators[session_id].values())
        return []
    
    def get_active_count(self, session_id: str) -> int:
        """获取会话中的活跃连接数"""
        if session_id in self.active_connections:
            return len(self.active_connections[session_id])
        return 0


# 全局连接管理器
manager = ConnectionManager()


# ============ 请求/响应模型 ============

class SessionCreate(BaseModel):
    """创建协作会话"""
    document_id: str
    name: Optional[str] = None
    max_collaborators: int = 10
    allow_anonymous: bool = False


class SessionResponse(BaseModel):
    """协作会话响应"""
    id: str
    document_id: str
    name: Optional[str] = None
    status: str
    current_version: int
    active_collaborators: int
    max_collaborators: int
    started_at: datetime
    last_activity_at: datetime
    created_at: datetime


class SessionListResponse(BaseModel):
    """协作会话列表响应"""
    items: List[SessionResponse]
    total: int
    page: int
    page_size: int


class CollaboratorResponse(BaseModel):
    """协作者响应"""
    id: str
    user_id: Optional[str] = None
    nickname: Optional[str] = None
    role: str
    is_online: bool
    color: Optional[str] = None
    cursor_position: Optional[dict] = None
    last_seen_at: datetime


class EditRecord(BaseModel):
    """编辑记录"""
    operation: str  # insert, delete, replace, format
    position: dict  # {start, end, line, column}
    content: Optional[str] = None
    old_content: Optional[str] = None


# ============ 协作会话路由 ============

@router.post("/sessions", response_model=UnifiedResponse)
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """创建协作会话"""
    # 检查文档是否存在
    doc_result = await db.execute(
        select(Document).where(Document.id == request.document_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        return UnifiedResponse.error(code=404, message="文档不存在")
    
    # 创建会话
    session = DocumentSession(
        document_id=request.document_id,
        name=request.name or f"协作会话-{document.name}",
        max_collaborators=request.max_collaborators,
        allow_anonymous=request.allow_anonymous,
        created_by=user.id if user else None,
        base_content=document.content if hasattr(document, 'content') else None,
        current_content=document.content if hasattr(document, 'content') else None,
    )
    
    db.add(session)
    await db.flush()
    
    # 创建者自动成为协作者
    if user:
        collaborator = DocumentCollaborator(
            session_id=session.id,
            user_id=user.id,
            role=CollaboratorRole.OWNER,
            nickname=user.username if hasattr(user, 'username') else user.email,
            color=_generate_color(),
        )
        db.add(collaborator)
        await db.flush()
    
    data = SessionResponse(
        id=session.id,
        document_id=session.document_id,
        name=session.name,
        status=session.status.value,
        current_version=session.current_version,
        active_collaborators=session.active_collaborators,
        max_collaborators=session.max_collaborators,
        started_at=session.started_at,
        last_activity_at=session.last_activity_at,
        created_at=session.created_at,
    )
    return UnifiedResponse.success(data=data)


class CommitRequest(BaseModel):
    """提交版本请求"""
    session_id: str
    message: str


@router.post("/sessions/{session_id}/commit", response_model=UnifiedResponse)
async def commit_session_version(
    session_id: str,
    request: CommitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交并创建一个新的文档版本"""
    service = CollaborationService(db)
    result = await service.create_version_snapshot(
        session_id=session_id,
        creator_id=user.id,
        message=request.message
    )
    if not result.get("success"):
        return UnifiedResponse.error(message=result.get("error", "提交失败"))
    
    # 广播版本更新
    await manager.broadcast(session_id, {
        "type": "version_committed",
        "version": result["version"],
        "message": request.message
    })
    
    return UnifiedResponse.success(data=result)


@router.get("/config", response_model=UnifiedResponse)
async def get_collaboration_config(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取协作系统配置（如 Docmost 地址）"""
    service = CollaborationService(db)
    config = await service.get_docmost_config()
    return UnifiedResponse.success(data=config)


@router.get("/sessions", response_model=UnifiedResponse)
async def list_sessions(
    document_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取协作会话列表"""
    from sqlalchemy import func, and_
    
    query = select(DocumentSession)
    count_query = select(func.count(DocumentSession.id))
    
    conditions = []
    if document_id:
        conditions.append(DocumentSession.document_id == document_id)
    if status:
        conditions.append(DocumentSession.status == SessionStatus(status))
    
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    # 总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页
    query = query.order_by(DocumentSession.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    sessions = list(result.scalars().all())
    
    data = SessionListResponse(
        items=[
            SessionResponse(
                id=s.id,
                document_id=s.document_id,
                name=s.name,
                status=s.status.value,
                current_version=s.current_version,
                active_collaborators=manager.get_active_count(s.id),
                max_collaborators=s.max_collaborators,
                started_at=s.started_at,
                last_activity_at=s.last_activity_at,
                created_at=s.created_at,
            )
            for s in sessions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(data=data)


@router.get("/sessions/{session_id}", response_model=UnifiedResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取协作会话详情"""
    result = await db.execute(
        select(DocumentSession).where(DocumentSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return UnifiedResponse.error(code=404, message="协作会话不存在")
    
    data = SessionResponse(
        id=session.id,
        document_id=session.document_id,
        name=session.name,
        status=session.status.value,
        current_version=session.current_version,
        active_collaborators=manager.get_active_count(session.id),
        max_collaborators=session.max_collaborators,
        started_at=session.started_at,
        last_activity_at=session.last_activity_at,
        created_at=session.created_at,
    )
    return UnifiedResponse.success(data=data)


@router.post("/sessions/{session_id}/close", response_model=UnifiedResponse)
async def close_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """关闭协作会话"""
    result = await db.execute(
        select(DocumentSession).where(DocumentSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return UnifiedResponse.error(code=404, message="协作会话不存在")
    
    session.status = SessionStatus.CLOSED
    session.ended_at = datetime.now()
    await db.flush()
    
    # 通知所有协作者会话已关闭
    await manager.broadcast(session_id, {
        "type": "session_closed",
        "message": "协作会话已关闭"
    })
    
    return UnifiedResponse.success(message="协作会话已关闭")


@router.get("/sessions/{session_id}/collaborators", response_model=UnifiedResponse)
async def get_collaborators(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取会话中的协作者列表"""
    result = await db.execute(
        select(DocumentCollaborator).where(
            DocumentCollaborator.session_id == session_id
        )
    )
    collaborators = list(result.scalars().all())
    
    # 更新在线状态
    online_users = manager.get_collaborators(session_id)
    online_user_ids = [c.get("user_id") for c in online_users]
    
    data = [
        CollaboratorResponse(
            id=c.id,
            user_id=c.user_id,
            nickname=c.nickname,
            role=c.role.value,
            is_online=c.user_id in online_user_ids,
            color=c.color,
            cursor_position=c.cursor_position,
            last_seen_at=c.last_seen_at,
        )
        for c in collaborators
    ]
    return UnifiedResponse.success(data=data)


# ============ WebSocket路由 ============

@router.websocket("/ws/{session_id}")
async def websocket_collaboration(
    websocket: WebSocket,
    session_id: str,
):
    """协作编辑WebSocket端点"""
    # 简化的认证：从查询参数获取用户信息
    user_id = websocket.query_params.get("user_id", str(uuid4()))
    nickname = websocket.query_params.get("nickname", f"用户{user_id[:4]}")
    color = websocket.query_params.get("color", _generate_color())
    
    # 验证会话
    async with async_session_maker() as db:
        result = await db.execute(
            select(DocumentSession).where(DocumentSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            await websocket.close(code=4004, reason="协作会话不存在")
            return
        
        if session.status != SessionStatus.ACTIVE:
            await websocket.close(code=4001, reason="协作会话已关闭")
            return
        
        # 检查协作者数量限制
        if manager.get_active_count(session_id) >= session.max_collaborators:
            await websocket.close(code=4002, reason="协作者数量已达上限")
            return
        
        # 创建或更新协作者记录
        collab_result = await db.execute(
            select(DocumentCollaborator).where(
                DocumentCollaborator.session_id == session_id,
                DocumentCollaborator.user_id == user_id
            )
        )
        collaborator = collab_result.scalar_one_or_none()
        
        if not collaborator:
            collaborator = DocumentCollaborator(
                session_id=session_id,
                user_id=user_id,
                nickname=nickname,
                color=color,
                role=CollaboratorRole.EDITOR,
            )
            db.add(collaborator)
        
        collaborator.is_online = True
        collaborator.last_seen_at = datetime.now()
        await db.commit()
        collaborator_id = collaborator.id
    
    # 连接WebSocket
    await manager.connect(
        websocket=websocket,
        session_id=session_id,
        user_id=user_id,
        user_info={
            "user_id": user_id,
            "nickname": nickname,
            "color": color,
            "collaborator_id": collaborator_id,
        }
    )
    
    # 广播用户加入
    await manager.broadcast(
        session_id=session_id,
        message={
            "type": "join",
            "user_id": user_id,
            "nickname": nickname,
            "color": color,
            "collaborators": manager.get_collaborators(session_id),
        },
        exclude_user=user_id
    )
    
    # 发送初始状态给新加入的用户
    async with async_session_maker() as db:
        result = await db.execute(
            select(DocumentSession).where(DocumentSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        await manager.send_personal(
            session_id=session_id,
            user_id=user_id,
            message={
                "type": "init",
                "content": session.current_content if session else "",
                "version": session.current_version if session else 1,
                "collaborators": manager.get_collaborators(session_id),
            }
        )
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "edit":
                # 处理编辑操作
                await _handle_edit(session_id, user_id, data)
            
            elif message_type == "cursor":
                # 处理光标移动
                await _handle_cursor(session_id, user_id, data)
            
            elif message_type == "ping":
                # 心跳响应
                await manager.send_personal(
                    session_id=session_id,
                    user_id=user_id,
                    message={"type": "pong"}
                )
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开: 用户 {user_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        # 断开连接
        manager.disconnect(session_id, user_id)
        
        # 更新协作者状态
        async with async_session_maker() as db:
            result = await db.execute(
                select(DocumentCollaborator).where(
                    DocumentCollaborator.session_id == session_id,
                    DocumentCollaborator.user_id == user_id
                )
            )
            collaborator = result.scalar_one_or_none()
            if collaborator:
                collaborator.is_online = False
                collaborator.left_at = datetime.now()
                await db.commit()
        
        # 广播用户离开
        await manager.broadcast(
            session_id=session_id,
            message={
                "type": "leave",
                "user_id": user_id,
                "collaborators": manager.get_collaborators(session_id),
            }
        )


async def _handle_edit(session_id: str, user_id: str, data: dict):
    """处理编辑操作"""
    operation = data.get("operation", "insert")
    position = data.get("position", {})
    content = data.get("content", "")
    old_content = data.get("old_content", "")
    
    async with async_session_maker() as db:
        # 获取会话
        result = await db.execute(
            select(DocumentSession).where(DocumentSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return
        
        # 获取协作者
        collab_result = await db.execute(
            select(DocumentCollaborator).where(
                DocumentCollaborator.session_id == session_id,
                DocumentCollaborator.user_id == user_id
            )
        )
        collaborator = collab_result.scalar_one_or_none()
        
        # 创建编辑记录
        edit = DocumentEdit(
            session_id=session_id,
            collaborator_id=collaborator.id if collaborator else None,
            operation=EditOperation(operation) if operation in [e.value for e in EditOperation] else EditOperation.INSERT,
            version=session.current_version + 1,
            position=position,
            content=content,
            old_content=old_content,
        )
        db.add(edit)
        
        # 更新会话版本和内容（简化处理）
        session.current_version += 1
        session.last_activity_at = datetime.now()
        session.total_edits += 1
        
        # 更新协作者编辑计数
        if collaborator:
            collaborator.edit_count += 1
            collaborator.last_seen_at = datetime.now()
        
        await db.commit()
    
    # 广播编辑操作给其他协作者
    await manager.broadcast(
        session_id=session_id,
        message={
            "type": "edit",
            "user_id": user_id,
            "operation": operation,
            "position": position,
            "content": content,
            "version": session.current_version,
        },
        exclude_user=user_id
    )


async def _handle_cursor(session_id: str, user_id: str, data: dict):
    """处理光标移动"""
    cursor_position = data.get("position", {})
    
    async with async_session_maker() as db:
        result = await db.execute(
            select(DocumentCollaborator).where(
                DocumentCollaborator.session_id == session_id,
                DocumentCollaborator.user_id == user_id
            )
        )
        collaborator = result.scalar_one_or_none()
        if collaborator:
            collaborator.cursor_position = cursor_position
            collaborator.last_seen_at = datetime.now()
            await db.commit()
    
    # 广播光标位置给其他协作者
    await manager.broadcast(
        session_id=session_id,
        message={
            "type": "cursor",
            "user_id": user_id,
            "position": cursor_position,
        },
        exclude_user=user_id
    )


def _generate_color() -> str:
    """生成随机颜色"""
    import random
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
        "#FFEAA7", "#DFE6E9", "#74B9FF", "#A29BFE",
        "#FD79A8", "#00B894", "#E17055", "#6C5CE7",
    ]
    return random.choice(colors)

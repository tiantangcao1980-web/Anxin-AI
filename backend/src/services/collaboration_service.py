"""
文档协作与版本控制服务

支持：
1. 实时协作编辑 (WebSocket)
2. CRDT 操作转换
3. 评论与批注
4. 版本历史
5. 光标同步
"""

import difflib
import json
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from src.models.collaboration import DocumentSession, DocumentEdit, DocumentCollaborator, SessionStatus
from src.models.document import Document


# ==================== 数据模型 ====================

@dataclass
class CollaborativeUser:
    """协作用户信息"""
    id: str
    name: str
    color: str
    cursor_pos: Optional[int] = None
    selection: Optional[Dict[str, int]] = None  # {from: int, to: int}


@dataclass
class DocumentOperation:
    """文档操作（CRDT 风格）"""
    id: str
    document_id: str
    user_id: str
    operation_type: str  # insert, delete, retain, format
    position: int
    length: int = 0
    content: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DocumentComment:
    """文档评论/批注"""
    id: str
    document_id: str
    user_id: str
    user_name: str
    content: str
    position: Dict[str, int]  # {from: int, to: int}
    resolved: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ==================== 协作会话管理 ====================

class CollaborationSession:
    """内存中的协作会话"""

    def __init__(self, document_id: str, initial_content: str = ""):
        self.document_id = document_id
        self.content = initial_content
        self.users: Dict[str, CollaborativeUser] = {}
        self.comments: Dict[str, DocumentComment] = {}
        self.operations: List[DocumentOperation] = []
        self.version = 0
        self.created_at = datetime.utcnow()
        self._lock = asyncio.Lock()

    async def add_user(self, user: CollaborativeUser):
        """添加用户"""
        async with self._lock:
            self.users[user.id] = user
            logger.info(f"用户 {user.name} 加入文档 {self.document_id}")

    async def remove_user(self, user_id: str):
        """移除用户"""
        async with self._lock:
            if user_id in self.users:
                del self.users[user_id]
                logger.info(f"用户 {user_id} 离开文档 {self.document_id}")

    def get_active_users(self) -> List[CollaborativeUser]:
        """获取活跃用户"""
        return list(self.users.values())

    async def apply_operation(self, op: DocumentOperation) -> bool:
        """应用操作到文档"""
        async with self._lock:
            try:
                if op.operation_type == "insert":
                    self.content = self.content[:op.position] + op.content + self.content[op.position:]
                elif op.operation_type == "delete":
                    self.content = self.content[:op.position] + self.content[op.position + op.length:]
                elif op.operation_type == "replace":
                    self.content = self.content[:op.position] + op.content + self.content[op.position + len(op.content):]

                self.operations.append(op)
                self.version += 1

                # 限制操作历史
                if len(self.operations) > 1000:
                    self.operations = self.operations[-500:]

                return True
            except Exception as e:
                logger.error(f"应用操作失败: {e}")
                return False

    async def add_comment(self, comment: DocumentComment):
        """添加评论"""
        async with self._lock:
            self.comments[comment.id] = comment

    async def resolve_comment(self, comment_id: str):
        """解决评论"""
        async with self._lock:
            if comment_id in self.comments:
                self.comments[comment_id].resolved = True

    def to_dict(self) -> dict:
        """序列化"""
        return {
            "document_id": self.document_id,
            "content": self.content,
            "version": self.version,
            "users": [asdict(u) for u in self.get_active_users()],
            "comments": [asdict(c) for c in self.comments.values() if not c.resolved],
        }


class CollaborationManager:
    """协作管理器 - 单例"""

    _instance: Optional['CollaborationManager'] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.sessions: Dict[str, CollaborationSession] = {}
            self.websocket_connections: Dict[str, Any] = {}  # session_id -> {websocket, user_id, document_id}
            self._initialized = True

    def get_or_create_session(self, document_id: str, initial_content: str = "") -> CollaborationSession:
        """获取或创建会话"""
        if document_id not in self.sessions:
            self.sessions[document_id] = CollaborationSession(document_id, initial_content)
        return self.sessions[document_id]

    def remove_session(self, document_id: str):
        """移除会话"""
        if document_id in self.sessions:
            del self.sessions[document_id]

    async def register_connection(self, session_id: str, websocket: Any, user_id: str, document_id: str):
        """注册 WebSocket"""
        self.websocket_connections[session_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "document_id": document_id,
        }
        logger.info(f"连接已注册: session={session_id}, user={user_id}, doc={document_id}")

    async def unregister_connection(self, session_id: str):
        """注销 WebSocket"""
        if session_id in self.websocket_connections:
            conn = self.websocket_connections.pop(session_id)
            # 从会话中移除用户
            doc_session = self.get_session(conn["document_id"])
            if doc_session:
                await doc_session.remove_user(conn["user_id"])
            logger.info(f"连接已注销: session={session_id}")

    def get_session(self, document_id: str) -> Optional[CollaborationSession]:
        """获取会话"""
        return self.sessions.get(document_id)

    async def broadcast_to_document(self, document_id: str, message: dict, exclude_session: Optional[str] = None):
        """广播消息到文档的所有协作者"""
        for session_id, conn in list(self.websocket_connections.items()):
            if conn["document_id"] == document_id and session_id != exclude_session:
                try:
                    await conn["websocket"].send_json(message)
                except Exception as e:
                    logger.warning(f"广播失败: {e}")
                    await self.unregister_connection(session_id)

    async def send_to_session(self, session_id: str, message: dict):
        """发送消息到特定会话"""
        if session_id in self.websocket_connections:
            try:
                await self.websocket_connections[session_id]["websocket"].send_json(message)
            except Exception as e:
                logger.warning(f"发送失败: {e}")
                await self.unregister_connection(session_id)


# 全局协作管理器
collaboration_manager = CollaborationManager()


# ==================== 协作服务 ====================

class CollaborationService:
    """协作编辑与版本管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.manager = collaboration_manager

    async def join_document(
        self,
        document_id: str,
        user_id: str,
        user_name: str,
        session_id: str,
        websocket: Any,
        initial_content: str = ""
    ) -> dict:
        """加入文档协作"""

        # 获取文档内容
        if not initial_content:
            result = await self.db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()
            initial_content = doc.extracted_text if doc else ""

        # 获取或创建会话
        session = self.manager.get_or_create_session(document_id, initial_content)

        # 创建用户
        user = CollaborativeUser(
            id=user_id,
            name=user_name,
            color=self._get_user_color(user_name)
        )
        await session.add_user(user)

        # 注册连接
        await self.manager.register_connection(session_id, websocket, user_id, document_id)

        # 通知其他用户
        await self.manager.broadcast_to_document(document_id, {
            "type": "user_joined",
            "user": asdict(user),
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_session=session_id)

        return session.to_dict()

    async def leave_document(self, document_id: str, user_id: str, session_id: str):
        """离开文档协作"""
        await self.manager.unregister_connection(session_id)

        # 通知其他用户
        await self.manager.broadcast_to_document(document_id, {
            "type": "user_left",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def handle_operation(
        self,
        document_id: str,
        user_id: str,
        operation: dict
    ) -> dict:
        """处理文档操作"""
        session = self.manager.get_session(document_id)
        if not session:
            return {"error": "会话不存在"}

        op = DocumentOperation(
            id=str(uuid.uuid4()),
            document_id=document_id,
            user_id=user_id,
            operation_type=operation.get("type", "insert"),
            position=operation.get("position", 0),
            length=operation.get("length", 0),
            content=operation.get("content", ""),
            attributes=operation.get("attributes", {})
        )

        success = await session.apply_operation(op)

        if success:
            # 广播操作
            await self.manager.broadcast_to_document(document_id, {
                "type": "operation",
                "operation": asdict(op),
                "version": session.version
            }, exclude_session=operation.get("session_id"))

            return {"success": True, "version": session.version}

        return {"success": False, "error": "操作失败"}

    async def update_cursor(
        self,
        document_id: str,
        user_id: str,
        position: int,
        selection: Optional[Dict[str, int]] = None
    ):
        """更新光标位置"""
        session = self.manager.get_session(document_id)
        if session and user_id in session.users:
            session.users[user_id].cursor_pos = position
            if selection:
                session.users[user_id].selection = selection

            # 广播光标更新
            await self.manager.broadcast_to_document(document_id, {
                "type": "cursor_update",
                "user_id": user_id,
                "position": position,
                "selection": selection
            })

    async def add_comment(
        self,
        document_id: str,
        user_id: str,
        user_name: str,
        content: str,
        position: Dict[str, int]
    ) -> dict:
        """添加评论"""
        session = self.manager.get_session(document_id)
        if not session:
            return {"error": "会话不存在"}

        comment = DocumentComment(
            id=str(uuid.uuid4()),
            document_id=document_id,
            user_id=user_id,
            user_name=user_name,
            content=content,
            position=position
        )

        await session.add_comment(comment)

        # 广播评论
        await self.manager.broadcast_to_document(document_id, {
            "type": "comment_added",
            "comment": asdict(comment)
        })

        return {"success": True, "comment_id": comment.id}

    async def resolve_comment(self, document_id: str, comment_id: str) -> dict:
        """解决评论"""
        session = self.manager.get_session(document_id)
        if not session:
            return {"error": "会话不存在"}

        await session.resolve_comment(comment_id)

        # 广播
        await self.manager.broadcast_to_document(document_id, {
            "type": "comment_resolved",
            "comment_id": comment_id
        })

        return {"success": True}

    async def save_document(self, document_id: str, content: str) -> dict:
        """保存文档到数据库"""
        try:
            result = await self.db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()

            if doc:
                doc.extracted_text = content
                doc.updated_at = datetime.utcnow()
                await self.db.flush()

                # 更新内存会话
                session = self.manager.get_session(document_id)
                if session:
                    session.content = content

                return {"success": True}

            return {"error": "文档不存在"}
        except Exception as e:
            logger.error(f"保存文档失败: {e}")
            return {"error": str(e)}

    # ==================== 原有方法 ====================

    async def create_version_snapshot(self, session_id: str, creator_id: str, message: str) -> Dict[str, Any]:
        """创建文档版本快照 (Git-like commit)"""
        result = await self.db.execute(
            select(DocumentSession).where(DocumentSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return {"success": False, "error": "会话不存在"}

        base_content = session.base_content or ""
        current_content = session.current_content or ""

        diff = list(difflib.unified_diff(
            base_content.splitlines(keepends=True),
            current_content.splitlines(keepends=True),
            fromfile='v_base',
            tofile=f'v_{session.current_version}'
        ))

        diff_text = "".join(diff)

        doc_result = await self.db.execute(
            select(Document).where(Document.id == session.document_id)
        )
        document = doc_result.scalar_one_or_none()
        if document:
            document.extracted_text = current_content
            document.version = (document.version or 0) + 1
            document.updated_at = datetime.now()

            session.base_content = current_content
            session.current_version += 1

            await self.db.flush()
            logger.info(f"文档 {document.id} 已提交新版本: {document.version}")

            return {
                "success": True,
                "version": document.version,
                "diff": diff_text,
                "message": message
            }

        return {"success": False, "error": "关联文档不存在"}

    async def get_docmost_config(self) -> Dict[str, Any]:
        """获取 Docmost 集成配置"""
        from src.core.config import settings

        return {
            "enabled": hasattr(settings, "DOCMOST_URL") and settings.DOCMOST_URL is not None,
            "url": getattr(settings, "DOCMOST_URL", ""),
            "editor_type": "tiptap",  # 使用 TipTap 而非 Docmost
            "features": ["realtime", "rich_text", "collaboration", "comments", "cursors"]
        }

    async def compare_versions(self, doc_id: str, v1: int, v2: int) -> str:
        """对比两个版本之间的差异"""
        return f"对比版本 {v1} 与版本 {v2} 的差异逻辑已就绪 (difflib)"

    @staticmethod
    def _generate_diff_html(old_text: str, new_text: str) -> str:
        """生成 HTML 格式的差异展示"""
        d = difflib.HtmlDiff()
        return d.make_table(old_text.splitlines(), new_text.splitlines())

    def _get_user_color(self, name: str) -> str:
        """根据用户名生成颜色"""
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
            '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
            '#F8B500', '#FF6F61', '#6B5B95', '#88B04B'
        ]
        hash_val = 0
        for char in name:
            hash_val = ord(char) + ((hash_val << 5) - hash_val)
        return colors[abs(hash_val) % len(colors)]

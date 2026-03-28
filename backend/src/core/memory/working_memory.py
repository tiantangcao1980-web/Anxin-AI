"""
工作记忆服务 (Working Memory)
负责存储短期会话状态
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import redis.asyncio as redis

from .base import BaseMemoryService


class WorkingMemoryService(BaseMemoryService):
    """
    工作记忆服务

    特性:
    - 会话级临时存储
    - 快速读写 (Redis)
    - 自动过期 (TTL 24h)
    - 支持 Agent 间状态共享
    """

    # 默认 TTL (24 小时)
    DEFAULT_TTL = 24 * 60 * 60

    # Redis 键前缀
    KEY_PREFIX = "working_memory:"

    def __init__(self, redis_url: str = None):
        super().__init__()
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None

    async def ensure_initialized(self):
        """确保 Redis 连接"""
        if not self._initialized:
            if self.redis_url:
                self.redis = redis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                await self.redis.ping()
                self._initialized = True
                self._log_info("工作记忆服务初始化完成")
            else:
                self._log_warning("未配置 Redis,工作记忆将使用内存存储")

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        创建新会话

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            metadata: 额外元数据

        Returns:
            是否创建成功
        """
        await self.ensure_initialized()

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "current_context": {},
            "active_tasks": [],
            "agent_states": {},
            "shared_variables": {},
            "retrieved_memories": {},
            "draft_content": "",
            "metadata": metadata or {}
        }

        return await self._set(session_id, session_data)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加消息到会话

        Args:
            session_id: 会话 ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            metadata: 额外元数据

        Returns:
            是否添加成功
        """
        session = await self.get(session_id)
        if not session:
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        session["messages"].append(message)
        return await self._set(session_id, session)

    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取会话消息

        Args:
            session_id: 会话 ID
            limit: 限制返回数量

        Returns:
            消息列表
        """
        session = await self.get(session_id)
        if not session:
            return []

        messages = session.get("messages", [])
        if limit:
            return messages[-limit:]
        return messages

    async def set_context(
        self,
        session_id: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        设置当前上下文

        Args:
            session_id: 会话 ID
            context: 上下文数据

        Returns:
            是否设置成功
        """
        session = await self.get(session_id)
        if not session:
            return False

        session["current_context"] = context
        return await self._set(session_id, session)

    async def get_context(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取当前上下文
        """
        session = await self.get(session_id)
        return session.get("current_context") if session else None

    async def set_agent_state(
        self,
        session_id: str,
        agent_name: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        设置 Agent 状态

        Args:
            session_id: 会话 ID
            agent_name: Agent 名称
            state: Agent 状态

        Returns:
            是否设置成功
        """
        session = await self.get(session_id)
        if not session:
            return False

        session["agent_states"][agent_name] = state
        return await self._set(session_id, session)

    async def get_agent_state(
        self,
        session_id: str,
        agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取 Agent 状态
        """
        session = await self.get(session_id)
        if not session:
            return None

        return session.get("agent_states", {}).get(agent_name)

    async def set_shared_variable(
        self,
        session_id: str,
        key: str,
        value: Any
    ) -> bool:
        """
        设置共享变量 (Agent 间通信)

        Args:
            session_id: 会话 ID
            key: 变量名
            value: 变量值

        Returns:
            是否设置成功
        """
        session = await self.get(session_id)
        if not session:
            return False

        session["shared_variables"][key] = value
        return await self._set(session_id, session)

    async def get_shared_variable(
        self,
        session_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        获取共享变量
        """
        session = await self.get(session_id)
        if not session:
            return default

        return session.get("shared_variables", {}).get(key, default)

    async def add_active_task(
        self,
        session_id: str,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> bool:
        """
        添加活动任务

        Args:
            session_id: 会话 ID
            task_id: 任务 ID
            task_data: 任务数据

        Returns:
            是否添加成功
        """
        session = await self.get(session_id)
        if not session:
            return False

        task = {
            "task_id": task_id,
            "started_at": datetime.now().isoformat(),
            "status": "active",
            **task_data
        }

        session["active_tasks"].append(task)
        return await self._set(session_id, session)

    async def complete_task(
        self,
        session_id: str,
        task_id: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        完成任务

        Args:
            session_id: 会话 ID
            task_id: 任务 ID
            result: 任务结果

        Returns:
            是否完成成功
        """
        session = await self.get(session_id)
        if not session:
            return False

        for task in session.get("active_tasks", []):
            if task["task_id"] == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.now().isoformat()
                task["result"] = result
                return await self._set(session_id, session)

        return False

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        await self.ensure_initialized()

        if self.redis:
            data = await self.redis.get(self._make_key(session_id))
            if data:
                return json.loads(data)
        return None

    async def add(self, data: Dict[str, Any]) -> Optional[str]:
        """添加 (用于兼容 BaseMemoryService)"""
        session_id = data.get("session_id") or data.get("id")
        if not session_id:
            return None

        success = await self._set(session_id, data)
        return session_id if success else None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索 (工作记忆不支持搜索)"""
        self._log_warning("工作记忆不支持搜索功能")
        return []

    async def update(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """更新会话数据"""
        session = await self.get(session_id)
        if not session:
            return False

        session.update(updates)
        return await self._set(session_id, session)

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        await self.ensure_initialized()

        if self.redis:
            await self.redis.delete(self._make_key(session_id))
            return True
        return False

    async def extend_ttl(
        self,
        session_id: str,
        additional_seconds: int = None
    ) -> bool:
        """
        延长会话 TTL

        Args:
            session_id: 会话 ID
            additional_seconds: 延长秒数 (默认使用 DEFAULT_TTL)

        Returns:
            是否延长成功
        """
        await self.ensure_initialized()

        if self.redis:
            ttl = additional_seconds or self.DEFAULT_TTL
            await self.redis.expire(self._make_key(session_id), ttl)
            return True
        return False

    async def clear_session(self, session_id: str) -> bool:
        """清空会话数据但保留会话"""
        session = await self.get(session_id)
        if not session:
            return False

        session["messages"] = []
        session["current_context"] = {}
        session["active_tasks"] = []
        session["draft_content"] = ""

        return await self._set(session_id, session)

    # ========== 私有方法 ==========

    def _make_key(self, session_id: str) -> str:
        """生成 Redis 键"""
        return f"{self.KEY_PREFIX}{session_id}"

    async def _set(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """设置会话数据"""
        await self.ensure_initialized()

        if self.redis:
            key = self._make_key(session_id)
            value = json.dumps(data, ensure_ascii=False)
            await self.redis.setex(key, self.DEFAULT_TTL, value)
            return True
        return False

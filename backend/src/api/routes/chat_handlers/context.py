# -*- coding: utf-8 -*-
"""
WebSocket 共享上下文

将 websocket_chat 中的闭包状态和辅助函数封装为类，
供各 handler 共享使用。
"""

import asyncio
import re
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional

from loguru import logger
from starlette.websockets import WebSocket

from src.services.a2ui_protocol import (
    a2ui_stream_start, a2ui_stream_component, a2ui_stream_end,
)


# 类型别名
WsCallback = Callable[[str, dict], Coroutine[Any, Any, None]]


class WebSocketContext:
    """
    WebSocket 会话上下文 — 封装一次 WebSocket 连接的所有共享状态。

    各 handler 通过 ctx 参数访问公共能力，而非依赖闭包。
    """

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        conversation_id: str,
        workforce,
    ):
        self.ws = websocket
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.workforce = workforce
        self._ws_closed = False
        self._save_lock = asyncio.Lock()
        self.session_message_count = 0
        self.last_user_content = ""

    # ---- 安全发送 ----

    async def send(self, event_type: str, data: dict):
        """安全发送 WebSocket 消息"""
        if self._ws_closed:
            return
        try:
            await self.ws.send_json({
                **data,
                "type": event_type,
                "session_id": self.session_id,
            })
        except Exception as e:
            if "close" in str(e).lower():
                self._ws_closed = True
            logger.warning(f"WS 发送失败: {e}")

    # ---- ws_callback（供 workforce 使用） ----

    async def ws_callback(self, event_type: str, data: dict):
        """统一回调 — 将 workforce 事件直接推送给前端"""
        await self.send(event_type, data)

    # ---- 消息持久化 ----

    async def save_message(
        self, role: str, content: str,
        agent_name: str = None,
        citations: Optional[list] = None,
    ):
        if not self.conversation_id:
            return
        async with self._save_lock:
            try:
                from src.core.database import async_session_maker
                from src.services.chat_service import ChatService
                async with async_session_maker() as db_session:
                    svc = ChatService(db_session)
                    await svc.add_message(
                        conversation_id=self.conversation_id, role=role,
                        content=content, agent_name=agent_name,
                        citations=citations,
                    )
                    # 第一条用户消息时，自动更新对话标题
                    if role == "user":
                        from src.models.conversation import Conversation as ConvModel
                        from sqlalchemy import select as sa_select, update as sa_update
                        result = await db_session.execute(
                            sa_select(ConvModel.title).where(
                                ConvModel.id == self.conversation_id
                            )
                        )
                        current_title = result.scalar_one_or_none()
                        if current_title and current_title.startswith("对话 "):
                            title_text = content.replace("[附件:", "").strip()[:50]
                            if title_text:
                                await db_session.execute(
                                    sa_update(ConvModel)
                                    .where(ConvModel.id == self.conversation_id)
                                    .values(title=title_text)
                                )
                                await self.send("conversation_title_updated", {
                                    "conversation_id": self.conversation_id,
                                    "title": title_text,
                                })
                    await db_session.commit()
            except Exception as e:
                logger.warning(f"WebSocket: 保存消息失败: {e}")
                await self.send("save_warning", {
                    "message": "消息可能未成功保存，建议刷新页面",
                })

    # ---- LLM 配置加载 ----

    async def load_llm_config(self):
        """加载 LLM 配置（优先使用缓存）"""
        try:
            from src.services.llm_service import LLMService
            return await LLMService.get_cached_effective_config("llm")
        except Exception:
            pass
        # 回退到数据库直查
        try:
            from src.core.database import async_session_maker
            from src.services.llm_service import LLMService
            async with async_session_maker() as db_session:
                cfg = await LLMService.get_default_config(db_session)
                if not cfg:
                    from src.models.llm_config import LLMConfig
                    from sqlalchemy import select
                    result_cfg = await db_session.execute(
                        select(LLMConfig)
                        .where(LLMConfig.config_type == "llm")
                        .where(LLMConfig.is_active == True)
                        .order_by(LLMConfig.updated_at.desc())
                        .limit(1)
                    )
                    cfg = result_cfg.scalar_one_or_none()
                return cfg
        except Exception as e:
            logger.warning(f"WebSocket: 加载LLM配置失败: {e}")
            return None

    # ---- 对话历史加载 ----

    async def load_recent_history(self, limit: int = 10) -> List[dict]:
        if not self.conversation_id:
            return []
        try:
            from src.core.database import async_session_maker
            from src.services.chat_service import ChatService
            async with async_session_maker() as db_session:
                svc = ChatService(db_session)
                return await svc.get_recent_history(
                    conversation_id=self.conversation_id,
                    limit=limit,
                    exclude_latest=True,
                )
        except Exception as e:
            logger.warning(f"WebSocket: 加载历史消息失败: {e}")
            return []

    # ---- 伪流式推送 ----

    async def stream_response_tokens(self, text: str, agent: str):
        """将完整响应文本逐块流式推送"""
        if not text:
            return
        chunks = re.split(r'([。！？；\n])', text)
        accumulated = ""
        buf = ""
        for chunk in chunks:
            buf += chunk
            if chunk in '。！？；\n' or len(buf) >= 30:
                if buf.strip():
                    accumulated += buf
                    await self.send("content_token", {
                        "token": buf,
                        "accumulated": accumulated,
                        "agent": agent,
                    })
                    await asyncio.sleep(0.02)
                buf = ""
        if buf.strip():
            accumulated += buf
            await self.send("content_token", {
                "token": buf,
                "accumulated": accumulated,
                "agent": agent,
            })

    # ---- 流式 A2UI 组件推送 ----

    async def stream_a2ui_components(
        self, components: list,
        agent: str = "AI 助手",
        stream_id: str = None,
        delay: float = 0.05,
    ):
        if not components:
            return
        sid = stream_id or f"stream-{str(uuid.uuid4())[:8]}"
        await self.send("a2ui_stream", a2ui_stream_start(sid, agent=agent))
        for comp in components:
            await self.send("a2ui_stream", a2ui_stream_component(sid, comp, agent=agent))
            if delay > 0:
                await asyncio.sleep(delay)
        await self.send("a2ui_stream", a2ui_stream_end(sid))

    # ---- 动态 max_tokens 估算 ----

    @staticmethod
    def estimate_max_tokens(content: str, complexity: str, intent: str = "") -> Optional[int]:
        if intent in ("DOCUMENT_DRAFTING", "CONTRACT_REVIEW", "EVIDENCE_PROCESSING"):
            return 4096
        if complexity == "simple" or len(content) < 20:
            return 512
        if complexity in ("moderate", "simple"):
            return 2048
        return 4096

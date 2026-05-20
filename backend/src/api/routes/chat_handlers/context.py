"""
WebSocket 共享上下文

将 websocket_chat 中的闭包状态和辅助函数封装为类，
供各 handler 共享使用。
"""

import asyncio
import re
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger
from starlette.websockets import WebSocket

from src.services.a2ui_protocol import (
    a2ui_stream_component,
    a2ui_stream_end,
    a2ui_stream_start,
)

# 类型别名
WsCallback = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


# 看起来像 UUID 或 hash 的文件名（纯十六进制或 UUID）
_UUID_LIKE_FILENAME = re.compile(r"^[0-9a-f\-]{16,}\.[a-zA-Z0-9]+$", re.IGNORECASE)


def _extract_conversation_title(content: str, max_length: int = 40) -> str:
    """
    从首条用户消息内容中提取对话标题。

    处理以下场景：
    1. 移除 "[附件: xxx]" 前缀
    2. 移除 "请结合附件「xxx」检索相关法规..." 等样板前缀
    3. 优先提取冒号后的实际需求（如 "...并整理要点结论：帮我分析一下"）
    4. 如果文件名是 UUID/hash 样式，替换为"附件"
    5. 去除换行、压缩空白、截断到 max_length
    """
    if not content:
        return ""

    text = content.strip()

    # 1. 移除 [附件: xxx] 前缀（可能有多个附件）
    text = re.sub(r"^\s*(?:\[附件:[^\]]*\]\s*\n?)+", "", text, flags=re.IGNORECASE)

    # 2. 压缩换行和多余空白
    text = re.sub(r"\s+", " ", text).strip()

    # 3. 识别"附件样板 + 冒号 + 实际需求"结构，截取冒号后的用户真实诉求
    #    例如: "请结合附件「xxx.pdf」检索...：帮我分析一下这份协议" → "帮我分析一下这份协议"
    template_prefixes = [
        r"^请结合附件[「『\"\"'']?[^」』\"\"'']*[」』\"\"'']?[^：:]*[：:]\s*",
        r"^结合附件[^：:]*[：:]\s*",
        r"^基于附件[^：:]*[：:]\s*",
    ]
    for pat in template_prefixes:
        new_text = re.sub(pat, "", text)
        if new_text != text and new_text:
            text = new_text
            break

    # 4. 如果文本以 UUID 样式文件名开头（意味着没匹配到模板），替换为"附件"
    text = re.sub(
        r"[「『\"\"'']?([0-9a-f\-]{16,}\.[a-zA-Z0-9]+)[」』\"\"'']?",
        "附件",
        text,
        flags=re.IGNORECASE,
    )

    # 5. 去除首尾标点和空白，截断
    text = text.strip(" 　,，.。!！?？:：;；")
    if len(text) > max_length:
        text = text[:max_length].rstrip() + "…"

    return text


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
        workforce: Any,
        user_id: str | None = None,
    ) -> None:
        self.ws = websocket
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.workforce = workforce
        # V2 安全修复（TASK-04 P0-2）：WS 顶层鉴权后由 websocket_chat 注入。
        # 缺失时 a2ui_handler / chat_handlers 内的 owner 校验会按"未知用户"拒绝。
        self.user_id: str | None = user_id
        self._ws_closed = False
        self._save_lock = asyncio.Lock()
        self.session_message_count = 0
        self.last_user_content = ""
        # V2：本轮对话的思考过程累积（send 时自动捕获）
        self._thinking_steps_buffer: list[dict[str, Any]] = []

    # ---- 安全发送 ----

    async def send(self, event_type: str, data: dict[str, Any]) -> None:
        """安全发送 WebSocket 消息"""
        if self._ws_closed:
            return
        # V2：自动捕获思考过程事件 → 累积到 buffer，供保存 AI 消息时一并持久化
        if event_type in ("thinking_content", "agent_thinking", "agent_start") and isinstance(
            data, dict
        ):
            try:
                content = data.get("content") or data.get("message") or ""
                if content:
                    self._thinking_steps_buffer.append(
                        {
                            "id": str(uuid.uuid4()),
                            "agent": data.get("agent", ""),
                            "content": str(content)[:1500],  # 限长防撑爆
                            "phase": data.get("phase", "execution"),
                            "timestamp": int(asyncio.get_event_loop().time() * 1000),
                        }
                    )
            except Exception:
                pass
        try:
            await self.ws.send_json(
                {
                    **data,
                    "type": event_type,
                    "session_id": self.session_id,
                }
            )
        except Exception as e:
            if "close" in str(e).lower():
                self._ws_closed = True
            logger.warning(f"WS 发送失败: {e}")

    def pop_thinking_steps(self) -> list[dict[str, Any]]:
        """取出本轮累积的思考步骤并清空（保存 AI 消息时调用）"""
        steps = list(self._thinking_steps_buffer)
        self._thinking_steps_buffer = []
        return steps

    # ---- ws_callback（供 workforce 使用） ----

    async def ws_callback(self, event_type: str, data: dict[str, Any]) -> None:
        """统一回调 — 将 workforce 事件直接推送给前端"""
        await self.send(event_type, data)

    # ---- 消息持久化（带自动重试） ----

    async def save_message(
        self,
        role: str,
        content: str,
        agent_name: str | None = None,
        citations: list[dict[str, Any]] | None = None,
        thinking_steps: list[dict[str, Any]] | None = None,
        memory_id: str | None = None,
    ) -> None:
        if not self.conversation_id:
            return
        async with self._save_lock:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    from src.core.database import async_session_maker
                    from src.services.chat_service import ChatService

                    async with async_session_maker() as db_session:
                        svc = ChatService(db_session)
                        # V2：保存 thinking_steps 与 memory_id 到 msg_metadata
                        _extra_meta: dict[str, Any] = {}
                        if thinking_steps:
                            _extra_meta["thinking_steps"] = thinking_steps
                        if memory_id:
                            _extra_meta["memory_id"] = memory_id
                        await svc.add_message(
                            conversation_id=self.conversation_id,
                            role=role,
                            content=content,
                            agent_name=agent_name,
                            citations=citations,
                            msg_metadata=_extra_meta if _extra_meta else None,
                        )
                        # 第一条用户消息时，自动更新对话标题
                        if role == "user":
                            from sqlalchemy import select as sa_select
                            from sqlalchemy import update as sa_update

                            from src.models.conversation import Conversation as ConvModel

                            result = await db_session.execute(
                                sa_select(ConvModel.title).where(
                                    ConvModel.id == self.conversation_id
                                )
                            )
                            current_title = result.scalar_one_or_none()
                            if current_title and current_title.startswith("对话 "):
                                title_text = _extract_conversation_title(content)
                                if title_text:
                                    await db_session.execute(
                                        sa_update(ConvModel)
                                        .where(ConvModel.id == self.conversation_id)
                                        .values(title=title_text)
                                    )
                                    await self.send(
                                        "conversation_title_updated",
                                        {
                                            "conversation_id": self.conversation_id,
                                            "title": title_text,
                                        },
                                    )
                        await db_session.commit()
                    # 成功 → 跳出重试循环
                    if attempt > 0:
                        logger.info(f"WebSocket: 消息保存成功（第 {attempt + 1} 次尝试）")
                    return
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 0.5 * (attempt + 1)
                        logger.warning(
                            f"WebSocket: 保存消息失败（第 {attempt + 1}/{max_retries} 次），{wait_time}s 后重试: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        # 最终失败：静默记录日志，不弹警告打扰用户
                        # 消息会在下次加载对话历史时从 Agent 响应中恢复
                        logger.error(f"WebSocket: 消息保存最终失败（已重试 {max_retries} 次）: {e}")

    # ---- LLM 配置加载 ----

    async def load_llm_config(self) -> Any:
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
                    from sqlalchemy import select

                    from src.models.llm_config import LLMConfig

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

    async def load_recent_history(self, limit: int = 10) -> list[dict[str, Any]]:
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

    async def stream_response_tokens(self, text: str, agent: str) -> None:
        """将完整响应文本逐块流式推送"""
        if not text:
            return
        chunks = re.split(r"([。！？；\n])", text)
        accumulated = ""
        buf = ""
        for chunk in chunks:
            buf += chunk
            if chunk in "。！？；\n" or len(buf) >= 30:
                if buf.strip():
                    accumulated += buf
                    await self.send(
                        "content_token",
                        {
                            "token": buf,
                            "accumulated": accumulated,
                            "agent": agent,
                        },
                    )
                    await asyncio.sleep(0.02)
                buf = ""
        if buf.strip():
            accumulated += buf
            await self.send(
                "content_token",
                {
                    "token": buf,
                    "accumulated": accumulated,
                    "agent": agent,
                },
            )

    # ---- 流式 A2UI 组件推送 ----

    async def stream_a2ui_components(
        self,
        components: list[dict[str, Any]],
        agent: str = "AI 助手",
        stream_id: str | None = None,
        delay: float = 0.05,
    ) -> None:
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
    def estimate_max_tokens(content: str, complexity: str, intent: str = "") -> int | None:
        if intent in ("DOCUMENT_DRAFTING", "CONTRACT_REVIEW", "EVIDENCE_PROCESSING"):
            return 4096
        if complexity == "simple" or len(content) < 20:
            return 512
        if complexity in ("moderate", "simple"):
            return 2048
        return 4096

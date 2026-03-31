# -*- coding: utf-8 -*-
"""
WebSocket 消息处理器模块

将原 websocket_chat 的 1000+ 行拆分为独立的处理器，
每个处理器负责一类消息的完整处理逻辑。

架构:
    WebSocketContext: 共享上下文（ws连接、发送函数、配置、辅助方法）
    各 Handler:      接收 context + data，返回是否已处理（bool）
"""

from src.api.routes.chat_handlers.context import WebSocketContext
from src.api.routes.chat_handlers.a2ui_handler import handle_a2ui_event
from src.api.routes.chat_handlers.workspace_handler import handle_workspace_message
from src.api.routes.chat_handlers.canvas_handler import handle_canvas_message
from src.api.routes.chat_handlers.due_diligence_handler import handle_due_diligence
from src.api.routes.chat_handlers.rag_handler import handle_rag_query

__all__ = [
    "WebSocketContext",
    "handle_a2ui_event",
    "handle_workspace_message",
    "handle_canvas_message",
    "handle_due_diligence",
    "handle_rag_query",
]

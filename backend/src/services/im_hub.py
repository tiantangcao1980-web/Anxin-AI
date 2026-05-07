"""
IM WebSocket 连接管理器

维护在线用户的 WebSocket 连接，支持多设备同时在线。
"""

from asyncio import Lock
from typing import Any

from fastapi import WebSocket
from loguru import logger
from starlette.websockets import WebSocketState

# 单用户最大同时连接数
MAX_CONNECTIONS_PER_USER = 5


class IMConnectionManager:
    """IM WebSocket 连接管理器"""

    def __init__(self) -> None:
        # user_id -> list[WebSocket]（支持多设备同时在线）
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._lock = Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> bool:
        """接受连接并注册，超过单用户最大连接数时拒绝"""
        async with self._lock:
            current_conns = self.active_connections.get(user_id, [])
            if len(current_conns) >= MAX_CONNECTIONS_PER_USER:
                if websocket.application_state != WebSocketState.CONNECTED:
                    await websocket.accept()
                await websocket.close(code=4029, reason="连接数超限")
                logger.warning(f"[IM] 用户 {user_id} 连接数超限（当前 {len(current_conns)}），拒绝新连接")
                return False
            if websocket.application_state != WebSocketState.CONNECTED:
                await websocket.accept()
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
            logger.info(f"[IM] 用户 {user_id} 已连接，当前设备数: {len(self.active_connections[user_id])}")
            return True

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """移除连接"""
        async with self._lock:
            conns = self.active_connections.get(user_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self.active_connections.pop(user_id, None)
            logger.info(f"[IM] 用户 {user_id} 断开连接")

    def is_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return bool(self.active_connections.get(user_id))

    def get_online_user_ids(self) -> list[str]:
        """获取所有在线用户 ID"""
        return list(self.active_connections.keys())

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """发送给用户的所有设备"""
        disconnected: list[WebSocket] = []
        for ws in self.active_connections.get(user_id, []):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"[IM] 向用户 {user_id} 发送消息失败: {e}")
                disconnected.append(ws)
        # 清理已断开的连接
        if disconnected:
            async with self._lock:
                conns = self.active_connections.get(user_id, [])
                for ws in disconnected:
                    if ws in conns:
                        conns.remove(ws)
                if not conns:
                    self.active_connections.pop(user_id, None)

    async def broadcast_to_conversation(
        self,
        participant_ids: list[str],
        message: dict[str, Any],
        exclude_user: str | None = None,
    ) -> None:
        """广播给对话内所有在线参与者"""
        for uid in participant_ids:
            if uid != exclude_user:
                await self.send_to_user(uid, message)

    async def push_notification(self, user_id: str, notification: dict[str, Any]) -> None:
        """通过 WebSocket 推送通知给用户"""
        payload = {
            "type": "notification",
            "notification": notification,
        }
        await self.send_to_user(user_id, payload)


# 全局单例
im_manager = IMConnectionManager()

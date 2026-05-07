"""
LiveKit RTC 服务

管理音视频通话房间和 Token 签发。
"""
from typing import Any, ClassVar

from loguru import logger

from src.core.config import settings


class RTCService:
    """LiveKit 房间管理和 Token 签发"""

    _api: ClassVar[Any | None] = None

    @classmethod
    def _get_api(cls) -> Any | None:
        if cls._api is not None:
            return cls._api

        if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY:
            logger.warning("LiveKit 未配置，音视频通话不可用")
            return None

        try:
            from livekit import api as lk_api
            cls._api = lk_api.LiveKitAPI(settings.LIVEKIT_URL)
            return cls._api
        except ImportError:
            logger.warning("livekit-api 未安装，请执行: pip install livekit-api")
            return None

    @classmethod
    def generate_token(
        cls,
        room_name: str,
        user_id: str,
        user_name: str,
        can_publish: bool = True,
        can_subscribe: bool = True,
    ) -> str | None:
        """生成前端连接 LiveKit 用的 JWT Token"""
        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            logger.warning("LiveKit 密钥未配置")
            return None

        try:
            from livekit import api as lk_api

            token = (
                lk_api.AccessToken(
                    api_key=settings.LIVEKIT_API_KEY,
                    api_secret=settings.LIVEKIT_API_SECRET,
                )
                .with_identity(user_id)
                .with_name(user_name)
                .with_grants(
                    lk_api.VideoGrants(
                        room_join=True,
                        room=room_name,
                        can_publish=can_publish,
                        can_subscribe=can_subscribe,
                    )
                )
                .to_jwt()
            )
            return token

        except Exception as e:
            logger.error(f"生成 LiveKit Token 失败: {e}")
            return None

    @classmethod
    async def create_room(cls, room_name: str) -> dict[str, Any] | None:
        """创建 LiveKit 房间"""
        api = cls._get_api()
        if not api:
            return None

        try:
            from livekit import api as lk_api
            room = await api.room.create_room(
                lk_api.CreateRoomRequest(name=room_name)
            )
            logger.info(f"LiveKit 房间已创建: {room_name}")
            return {"name": room.name, "sid": room.sid}
        except Exception as e:
            logger.error(f"创建 LiveKit 房间失败: {e}")
            return None

    @classmethod
    async def delete_room(cls, room_name: str) -> bool:
        """删除 LiveKit 房间"""
        api = cls._get_api()
        if not api:
            return False

        try:
            from livekit import api as lk_api
            await api.room.delete_room(
                lk_api.DeleteRoomRequest(room=room_name)
            )
            logger.info(f"LiveKit 房间已删除: {room_name}")
            return True
        except Exception as e:
            logger.error(f"删除 LiveKit 房间失败: {e}")
            return False

    @classmethod
    async def list_rooms(cls) -> list[dict[str, Any]]:
        """列出所有活跃房间"""
        api = cls._get_api()
        if not api:
            return []

        try:
            from livekit import api as lk_api
            resp = await api.room.list_rooms(lk_api.ListRoomsRequest())
            return [
                {
                    "name": r.name,
                    "sid": r.sid,
                    "num_participants": r.num_participants,
                    "creation_time": r.creation_time,
                }
                for r in resp.rooms
            ]
        except Exception as e:
            logger.error(f"列出 LiveKit 房间失败: {e}")
            return []

    @classmethod
    def is_available(cls) -> bool:
        """检查 LiveKit 是否可用"""
        return bool(settings.LIVEKIT_URL and settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET)


rtc_service = RTCService()

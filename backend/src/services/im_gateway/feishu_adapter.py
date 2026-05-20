"""
飞书（Lark）IM 适配器 — P3 真实现

要点：
    1. ``tenant_access_token`` Redis 缓存（2h 自动续期，过期前 5 分钟刷新）
    2. ``send_message`` 支持 text / interactive (卡片) / post (富文本)
    3. ``receive_webhook`` 支持 URL 验证（challenge 快速路径）+ 加密 payload
       解密 + 签名校验 + 事件路由
    4. ``register_bot`` 把通道写入 ``IMChannel`` 表
    5. ``list_groups`` 分页拉群（``page_size=100``）

依赖：``cryptography``（已通过 python-jose[cryptography] 间接安装）、
``httpx``、``redis``、``loguru``。
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
from loguru import logger

from src.services.im_gateway.base import BaseIMAdapter
from src.services.im_gateway.feishu_signature import (
    FeishuSignatureError,
    FeishuTimestampError,
    decrypt_payload,
    verify_signature,
)
from src.services.im_gateway.models import IMChannelType

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
FEISHU_OPEN_API_BASE = "https://open.feishu.cn/open-apis"
TENANT_TOKEN_URL = f"{FEISHU_OPEN_API_BASE}/auth/v3/tenant_access_token/internal"
SEND_MESSAGE_URL = f"{FEISHU_OPEN_API_BASE}/im/v1/messages"
LIST_CHATS_URL = f"{FEISHU_OPEN_API_BASE}/im/v1/chats"

# token 过期前多久刷新（飞书 token 默认 7200s，提前 300s 续期）
TOKEN_REFRESH_LEEWAY_SECONDS = 300

# HTTP 默认超时与重试（与 BaseIMAdapter 设计目标一致：异步 + 短超时）
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)
DEFAULT_RETRIES = 2  # 不含首次请求


class FeishuAdapter(BaseIMAdapter):
    """飞书 IM 适配器（P3 真实现）。

    config 字段（来自 ``IMChannel.config`` 或 settings 兜底）：
        - ``app_id``         : 必填
        - ``app_secret``     : 必填
        - ``encrypt_key``    : 加密推送时必填
        - ``verify_token``   : 事件订阅校验
        - ``redis_url``      : 缓存 token 用（可选，缺省取 settings.REDIS_URL）
    """

    channel_type: str = IMChannelType.FEISHU.value

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
        redis_client: Any | None = None,
    ) -> None:
        super().__init__(config)

        # 从 config 或 settings 解析配置（settings 作兜底，便于本地开发）
        try:
            from src.core.config import settings as _settings

            self._settings = _settings
        except Exception:  # pragma: no cover - 极端情况下 settings 不可用
            self._settings = None

        self._app_id: str = self.config.get("app_id") or self._setting("FEISHU_APP_ID")
        self._app_secret: str = self.config.get("app_secret") or self._setting("FEISHU_APP_SECRET")
        self._encrypt_key: str = self.config.get("encrypt_key") or self._setting(
            "FEISHU_ENCRYPT_KEY"
        )
        self._verify_token: str = self.config.get("verify_token") or self._setting(
            "FEISHU_VERIFY_TOKEN"
        )

        # 可注入的 client（测试时用 mock）
        self._http_client: httpx.AsyncClient | None = http_client
        self._redis_client = redis_client
        self._token_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _setting(self, name: str) -> str:
        """从 settings 读取字符串字段，缺失返回空串。"""
        if self._settings is None:
            return ""
        return getattr(self._settings, name, "") or ""

    async def _get_http(self) -> httpx.AsyncClient:
        """惰性创建 httpx AsyncClient（适配器实例级共享连接池）。"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        return self._http_client

    async def _get_redis(self) -> Any | None:
        """惰性创建 Redis 客户端，失败时返回 None（降级为内存缓存）。"""
        if self._redis_client is not None:
            return self._redis_client
        try:
            import redis.asyncio as aioredis  # noqa: WPS433 — 局部导入避免硬依赖

            redis_url = (
                self.config.get("redis_url")
                or self._setting("REDIS_URL")
                or "redis://localhost:6379/0"
            )
            self._redis_client = aioredis.from_url(redis_url, decode_responses=True)
            return self._redis_client
        except Exception as e:  # pragma: no cover
            logger.warning(f"飞书适配器无法连接 Redis ({e})，token 改用内存缓存")
            return None

    def _token_cache_key(self) -> str:
        return f"im:feishu:tenant_token:{self._app_id or 'unknown'}"

    # ---------------- token 获取 + 缓存 ----------------
    async def _get_tenant_access_token(self) -> str:
        """获取 ``tenant_access_token``（带 Redis 缓存 + 过期前续期）。"""
        if not self._app_id or not self._app_secret:
            raise RuntimeError("飞书 app_id/app_secret 未配置，无法获取 tenant_access_token")

        cache_key = self._token_cache_key()
        redis = await self._get_redis()

        # 1. 命中缓存直接返回
        if redis is not None:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    return cached
            except Exception as e:  # pragma: no cover
                logger.warning(f"飞书 token Redis 读取失败: {e}")

        # 2. 加锁防雪崩
        async with self._token_lock:
            if redis is not None:
                try:
                    cached = await redis.get(cache_key)
                    if cached:
                        return cached
                except Exception:  # pragma: no cover
                    pass

            token, expire_in = await self._fetch_tenant_access_token()

            # 提前续期：写入 Redis，TTL = 飞书过期时间 - 5 分钟
            ttl = max(60, expire_in - TOKEN_REFRESH_LEEWAY_SECONDS)
            if redis is not None:
                try:
                    await redis.set(cache_key, token, ex=ttl)
                except Exception as e:  # pragma: no cover
                    logger.warning(f"飞书 token Redis 写入失败: {e}")
            return token

    async def _fetch_tenant_access_token(self) -> tuple[str, int]:
        """调用 ``/auth/v3/tenant_access_token/internal`` 获取新 token。

        返回 ``(token, expire_in_seconds)``。
        """
        client = await self._get_http()
        payload = {"app_id": self._app_id, "app_secret": self._app_secret}
        resp = await client.post(TENANT_TOKEN_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(
                f"飞书 tenant_access_token 失败: code={data.get('code')} " f"msg={data.get('msg')}"
            )
        return data["tenant_access_token"], int(data.get("expire", 7200))

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """带重试的 HTTP 调用（指数退避，token 失效自动刷新一次）。"""
        client = await self._get_http()
        last_err: Exception | None = None

        for attempt in range(DEFAULT_RETRIES + 1):
            try:
                token = await self._get_tenant_access_token()
                headers = {"Authorization": f"Bearer {token}"}
                resp = await client.request(
                    method, url, json=json_body, params=params, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
                code = data.get("code", 0)

                # token 失效（飞书错误码 99991663/99991664）— 强制刷新一次
                if code in (99991663, 99991664) and attempt < DEFAULT_RETRIES:
                    redis = await self._get_redis()
                    if redis is not None:
                        try:
                            await redis.delete(self._token_cache_key())
                        except Exception:  # pragma: no cover
                            pass
                    continue

                if code != 0:
                    raise RuntimeError(
                        f"飞书 API 返回错误: code={code} msg={data.get('msg')} url={url}"
                    )
                return data
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last_err = e
                if attempt >= DEFAULT_RETRIES:
                    break
                await asyncio.sleep(0.5 * (2**attempt))

        raise RuntimeError(f"飞书 API 调用失败: {url} → {last_err}")

    # ------------------------------------------------------------------
    # 1. send_message
    # ------------------------------------------------------------------
    async def send_message(
        self,
        channel_id: str,
        content: str,
        msg_type: str = "text",
        **extra: Any,
    ) -> dict[str, Any]:
        """向某个 chat 发送一条消息。

        ``msg_type`` 支持：
            - ``text``         : ``content`` 即纯文本
            - ``interactive``  : ``content`` 应是 ``json.dumps(card)``，
                                  或通过 ``extra['card']=dict`` 传卡片
            - ``post``         : ``content`` 应是 ``json.dumps(post_payload)``
        """
        if msg_type == "interactive" and "card" in extra:
            content_str = json.dumps(extra["card"], ensure_ascii=False)
        elif isinstance(content, (dict, list)):
            content_str = json.dumps(content, ensure_ascii=False)
        else:
            # text 类型飞书要求 ``{"text": "..."}`` 字符串
            if msg_type == "text" and not (content.startswith("{") and "text" in content):
                content_str = json.dumps({"text": content}, ensure_ascii=False)
            else:
                content_str = content

        payload = {
            "receive_id": channel_id,
            "msg_type": msg_type,
            "content": content_str,
        }
        if extra.get("uuid"):
            payload["uuid"] = extra["uuid"]

        # ``receive_id_type`` 默认 chat_id；可由 extra 覆盖（open_id/email/...）
        receive_id_type = extra.get("receive_id_type", "chat_id")
        url = f"{SEND_MESSAGE_URL}?receive_id_type={receive_id_type}"

        return await self._request_with_retry("POST", url, json_body=payload)

    # ------------------------------------------------------------------
    # 2. receive_webhook
    # ------------------------------------------------------------------
    async def receive_webhook(
        self,
        payload: dict[str, Any] | bytes | str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """处理飞书事件回调。

        参数：
            payload: 原始 body —— 优先传 ``bytes``（以便签名校验），
                     也接受已反序列化的 dict（跳过签名）
            headers: HTTP 头，需要：
                - ``X-Lark-Request-Timestamp``
                - ``X-Lark-Request-Nonce``
                - ``X-Lark-Signature``

        返回：
            归一化的内部事件字典：
                {
                    "kind": "url_verification" | "event" | "card_action",
                    "channel_type": "feishu",
                    "external_user_id": str | None,
                    "event_type": str | None,
                    "data": dict,
                }

        URL 验证（``challenge``）走快速路径，无需签名校验，直接回填
        ``{"challenge": ...}`` 给路由层。
        """
        headers = headers or {}

        # 1) 反序列化 body（保留原始 bytes 用于签名）
        if isinstance(payload, (bytes, bytearray)):
            raw_body = bytes(payload)
            try:
                body_obj: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
            except Exception as e:
                raise ValueError(f"飞书 webhook body 不是合法 JSON: {e}") from e
        elif isinstance(payload, str):
            raw_body = payload.encode("utf-8")
            body_obj = json.loads(payload)
        else:
            body_obj = payload
            raw_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        # 2) 加密推送：先解密拿到真实 body
        if "encrypt" in body_obj:
            body_obj = decrypt_payload(body_obj["encrypt"], self._encrypt_key)

        # 3) URL 验证快速路径（无需签名）
        if body_obj.get("type") == "url_verification" or "challenge" in body_obj:
            return {
                "kind": "url_verification",
                "channel_type": self.channel_type,
                "external_user_id": None,
                "event_type": "url_verification",
                "data": {"challenge": body_obj.get("challenge", "")},
            }

        # 4) 签名校验（P16-C：fail-closed —— encrypt_key 缺失会抛 FeishuSignatureError，
        #    除非 FEISHU_VERIFY_SIGNATURE=False 显式关闭；timestamp 超 ±300s 抛 FeishuTimestampError）
        timestamp = headers.get("X-Lark-Request-Timestamp", "")
        nonce = headers.get("X-Lark-Request-Nonce", "")
        signature = headers.get("X-Lark-Signature", "")
        try:
            ok = verify_signature(timestamp, nonce, raw_body, signature, self._encrypt_key)
        except FeishuTimestampError as e:
            raise PermissionError(f"飞书 webhook timestamp 校验失败: {e}") from e
        except FeishuSignatureError as e:
            raise PermissionError(f"飞书 webhook 签名校验未启用: {e}") from e
        if not ok:
            raise PermissionError("飞书 webhook 签名校验失败")

        # 5) 事件路由（schema v2 + 兼容 v1）
        # v2: { "schema": "2.0", "header": {...}, "event": {...} }
        # v1: { "type": "event_callback", "event": {...} }
        header = body_obj.get("header") or {}
        event_type = header.get("event_type") or body_obj.get("event", {}).get("type", "unknown")
        event_data = body_obj.get("event", {})

        # 卡片回调（按钮点击）
        if event_type == "card.action.trigger":
            return {
                "kind": "card_action",
                "channel_type": self.channel_type,
                "external_user_id": event_data.get("operator", {}).get("open_id"),
                "event_type": event_type,
                "data": event_data,
            }

        # 普通消息
        sender = event_data.get("sender", {}) or {}
        sender_id = (sender.get("sender_id") or {}).get("open_id") or sender.get("open_id")
        return {
            "kind": "event",
            "channel_type": self.channel_type,
            "external_user_id": sender_id,
            "event_type": event_type,
            "data": event_data,
        }

    # ------------------------------------------------------------------
    # 3. register_bot
    # ------------------------------------------------------------------
    async def register_bot(self, config: dict[str, Any]) -> dict[str, Any]:
        """把 bot 注册信息写入 ``IMChannel`` 表。

        如果传入 ``session`` (AsyncSession) 则真写入 DB；否则返回准备好的
        模型字段 dict（由路由层决定何时持久化）。

        必填 config：``app_id``、``app_secret``、``name``。
        可选：``encrypt_key`` / ``verify_token`` / ``webhook_url``。
        """
        for k in ("app_id", "app_secret", "name"):
            if not config.get(k):
                raise ValueError(f"register_bot 缺少必填字段: {k}")

        record = {
            "channel_type": IMChannelType.FEISHU,
            "name": config["name"],
            "config": {
                "app_id": config["app_id"],
                "app_secret": config["app_secret"],
                "encrypt_key": config.get("encrypt_key", ""),
                "verify_token": config.get("verify_token", ""),
                "webhook_url": config.get("webhook_url", ""),
            },
            "enabled": config.get("enabled", True),
        }

        session = config.get("session")
        if session is not None:
            from src.services.im_gateway.models import IMChannel

            channel = IMChannel(**record)
            session.add(channel)
            await session.flush()
            return {
                "id": str(channel.id),
                "channel_type": channel.channel_type.value,
                "name": channel.name,
                "enabled": channel.enabled,
                "registered_at": int(time.time()),
            }

        # 未传 session：返回 dry-run record
        return {
            "dry_run": True,
            "record": record,
            "registered_at": int(time.time()),
        }

    # ------------------------------------------------------------------
    # 4. list_groups
    # ------------------------------------------------------------------
    async def list_groups(self) -> list[dict[str, Any]]:
        """分页拉取 bot 所在的群列表（``page_size=100``）。"""
        groups: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            params: dict[str, Any] = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            data = await self._request_with_retry("GET", LIST_CHATS_URL, params=params)
            items = (data.get("data") or {}).get("items") or []
            for item in items:
                groups.append(
                    {
                        "id": item.get("chat_id"),
                        "name": item.get("name") or item.get("description") or "",
                        "type": "group" if item.get("chat_mode") == "group" else "im",
                        "raw": item,
                    }
                )

            page_token = (data.get("data") or {}).get("page_token")
            has_more = (data.get("data") or {}).get("has_more")
            if not has_more or not page_token:
                break

        return groups

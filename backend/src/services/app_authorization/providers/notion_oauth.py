# -*- coding: utf-8 -*-
"""Notion OAuth 2.0 Provider — P4-D 真实现。

实装 ``BaseOAuthProvider`` 的 5 个方法，对接 Notion 开放平台 OAuth：

    * ``authorize_url``   — 拼装授权页 URL（owner=user, response_type=code）
    * ``exchange_code``   — code → access_token + workspace 元信息
    * ``refresh_token``   — Notion **不支持**刷新（access_token 永不过期）
                             → 显式抛 :class:`NotImplementedError`
    * ``revoke``          — Basic Auth + ``DELETE /v1/oauth/revoke``
    * ``get_user_info``   — Bearer token + ``Notion-Version: 2022-06-28``

参考文档：https://developers.notion.com/docs/authorization

技术要点（与飞书/Google 不同，需特别注意）：

    1. **Basic Auth 鉴权**：``/v1/oauth/token`` 与 ``/v1/oauth/revoke`` 必须使用
       ``Authorization: Basic base64(client_id:client_secret)`` 头，
       而不是把 client_secret 放在 body 里。
    2. **不支持 refresh_token**：Notion 的 access_token 永久有效（除非用户
       主动撤销或 workspace owner 卸载集成）。所以 ``refresh_token`` 方法
       应显式抛错，让上层在 token_store 层完全不存 refresh_token。
    3. **Notion-Version 必传**：所有 Notion REST API 请求都必须带
       ``Notion-Version`` 头，否则 400。本 provider 锁定 ``2022-06-28``。
    4. **scope 不参与协议**：Notion 在授权页让用户选择 page/database 粒度，
       因此 ``default_scopes = []``，``authorize_url`` 也不传 scope 参数。
    5. **owner=user**：表示按用户授权（个人 workspace）；
       ``owner=workspace`` 用于 enterprise SSO 场景（暂不支持）。
    6. HTTP 429 限流走指数退避重试（最多 3 次），与飞书 provider 对齐。

⚠️ 文件边界：本 provider **只**使用 ``..base`` 暴露的契约，
不修改 P4-A 的任何骨架文件。
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any
from urllib.parse import urlencode

import httpx

from ..base import (
    BaseOAuthProvider,
    OAuthError,
    OAuthTokenBundle,
)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
NOTION_API_BASE = "https://api.notion.com"

# 授权页（用户跳转）
AUTHORIZE_URL = f"{NOTION_API_BASE}/v1/oauth/authorize"
# token 接口（POST + Basic Auth）
TOKEN_URL = f"{NOTION_API_BASE}/v1/oauth/token"
# 撤销接口（DELETE + Basic Auth）
REVOKE_URL = f"{NOTION_API_BASE}/v1/oauth/revoke"
# 当前用户信息（Bearer token）
USER_INFO_URL = f"{NOTION_API_BASE}/v1/users/me"

# Notion REST API 版本（所有请求强制要求该 Header）
NOTION_VERSION = "2022-06-28"

# HTTP 超时（秒）
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)

# 429 限流时的最大重试次数（不含首次请求）
MAX_RETRIES_ON_RATE_LIMIT = 3


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------
class NotionOAuthProvider(BaseOAuthProvider):
    """Notion OAuth provider。

    ``default_scopes = []`` 的原因：Notion OAuth 不使用 OAuth scope 概念，
    用户在授权页直接勾选要授权的 page / database，由 Notion 自己持久化范围。
    因此 :meth:`authorize_url` 不会附带 ``scope=`` 参数。
    """

    provider_id = "notion"
    display_name = "Notion"
    category = "office"
    icon_url = "https://www.notion.so/images/logo-ios.png"
    default_scopes: list[str] = []

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """构造一个 Notion OAuth provider。

        Args:
            client_id: Notion integration 的 OAuth client_id。
                       缺省则读取 ``settings.NOTION_CLIENT_ID``。
            client_secret: integration secret。缺省读 ``settings.NOTION_CLIENT_SECRET``。
            http_client: 可注入的 ``httpx.AsyncClient``（用于测试 mock）。
        """
        # 复用项目 settings；测试场景下 settings 可能不可用，做兜底
        settings_client_id = ""
        settings_client_secret = ""
        try:  # pragma: no cover - 依赖项目运行时配置
            from src.core.config import settings as _settings

            settings_client_id = getattr(_settings, "NOTION_CLIENT_ID", "") or ""
            settings_client_secret = getattr(_settings, "NOTION_CLIENT_SECRET", "") or ""
        except Exception:
            pass

        self._client_id: str = client_id or settings_client_id
        self._client_secret: str = client_secret or settings_client_secret
        self._http_client: httpx.AsyncClient | None = http_client

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    async def _get_http(self) -> httpx.AsyncClient:
        """惰性创建 ``httpx.AsyncClient``（实例级共享连接池）。"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        return self._http_client

    def _ensure_credentials(self) -> None:
        """确保 client_id / client_secret 已配置；否则抛 :class:`OAuthError`。"""
        if not self._client_id or not self._client_secret:
            raise OAuthError(
                "Notion OAuth 未配置：缺少 NOTION_CLIENT_ID 或 NOTION_CLIENT_SECRET"
            )

    def _basic_auth_header(self) -> str:
        """生成 ``Authorization: Basic base64(client_id:client_secret)`` 头值。

        Notion ``/v1/oauth/token`` 与 ``/v1/oauth/revoke`` 强制要求该方式，
        client_secret **不可**放在 JSON body 里。
        """
        creds = f"{self._client_id}:{self._client_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(creds).decode("ascii")

    @staticmethod
    def _notion_version_header() -> dict[str, str]:
        """所有 Notion REST API 请求都必须附带的版本头。"""
        return {"Notion-Version": NOTION_VERSION}

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """带 429 指数退避重试的 HTTP 调用。

        Notion 接口的失败语义：
            * 网络错误 / 5xx → 指数退避重试
            * HTTP 429 → 同样指数退避重试（最多 ``MAX_RETRIES_ON_RATE_LIMIT`` 次）
            * HTTP 4xx（非 429） → :class:`OAuthError`

        Returns:
            解析后的 JSON dict（空响应返回 ``{}``）。
        """
        client = await self._get_http()
        last_err: Exception | None = None

        for attempt in range(MAX_RETRIES_ON_RATE_LIMIT + 1):
            try:
                resp = await client.request(
                    method, url, json=json_body, params=params, headers=headers
                )

                # 429 限流：指数退避后重试
                if resp.status_code == 429 and attempt < MAX_RETRIES_ON_RATE_LIMIT:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue

                resp.raise_for_status()

                # 部分接口（如 revoke）可能返回空 body
                if not resp.content:
                    return {}
                try:
                    return resp.json()
                except ValueError:
                    return {}

            except httpx.HTTPStatusError as e:
                last_err = e
                # 5xx 走重试，4xx（除 429 已上面处理）直接抛
                if e.response is not None and e.response.status_code < 500:
                    raise OAuthError(
                        f"Notion OAuth HTTP {e.response.status_code} 错误: {url}"
                    ) from e
                if attempt >= MAX_RETRIES_ON_RATE_LIMIT:
                    break
                await asyncio.sleep(0.5 * (2**attempt))
            except httpx.TransportError as e:
                last_err = e
                if attempt >= MAX_RETRIES_ON_RATE_LIMIT:
                    break
                await asyncio.sleep(0.5 * (2**attempt))

        raise OAuthError(
            f"Notion OAuth 调用失败（已重试 {MAX_RETRIES_ON_RATE_LIMIT} 次）: {url} → {last_err}"
        )

    # ------------------------------------------------------------------
    # 1. authorize_url —— 生成跳转授权页
    # ------------------------------------------------------------------
    async def authorize_url(
        self,
        state: str,
        redirect_uri: str,
        scopes: list[str] | None = None,  # noqa: ARG002 — Notion 不用 scope
    ) -> str:
        """生成 Notion OAuth 授权页 URL。

        Args:
            state: 防 CSRF 的随机串，前端回跳时回传校验。
            redirect_uri: Notion integration 后台已登记的回跳地址。
            scopes: **被忽略**——Notion 通过授权页直接选 page/database 粒度。

        Returns:
            完整的 ``https://api.notion.com/v1/oauth/authorize?...`` URL。
        """
        self._ensure_credentials()

        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "owner": "user",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    # ------------------------------------------------------------------
    # 2. exchange_code —— code → access_token + workspace 元信息
    # ------------------------------------------------------------------
    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokenBundle:
        """使用授权码换取 access_token，同时拿到 workspace 元信息。

        Notion 返回结构示例：

            {
                "access_token": "secret_xxx",
                "bot_id": "...",
                "workspace_name": "Acme Co",
                "workspace_icon": "https://...",
                "workspace_id": "...",
                "owner": {...},
                "duplicated_template_id": null
            }

        Notion **不返回** ``expires_in`` / ``refresh_token``——access_token 永久有效。
        Workspace 元信息全部塞入 ``OAuthTokenBundle.raw``，由上层 token_store
        持久化（用于在 UI 显示「已绑定 Acme Co」等信息）。

        Args:
            code: Notion 回跳带回的一次性授权码。
            redirect_uri: 与 :meth:`authorize_url` 中保持一致的回跳地址。

        Returns:
            :class:`OAuthTokenBundle`，``raw`` 含 workspace 全部字段。
        """
        self._ensure_credentials()

        body = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        headers = {
            "Authorization": self._basic_auth_header(),
            "Content-Type": "application/json",
            **self._notion_version_header(),
        }
        data = await self._request_with_retry(
            "POST", TOKEN_URL, json_body=body, headers=headers
        )

        access_token = data.get("access_token") or ""
        if not access_token:
            raise OAuthError(f"Notion token 响应缺少 access_token: {data!r}")

        return OAuthTokenBundle(
            access_token=access_token,
            refresh_token=None,           # Notion 不支持刷新
            expires_in=None,              # access_token 永久有效
            scope=None,                   # Notion 不使用 scope
            token_type=data.get("token_type", "Bearer"),
            raw=data,                     # workspace_name / workspace_id / bot_id / owner ...
        )

    # ------------------------------------------------------------------
    # 3. refresh_token —— 不支持
    # ------------------------------------------------------------------
    async def refresh_token(self, refresh_token: str) -> OAuthTokenBundle:  # noqa: ARG002
        """**Notion 不支持 refresh_token**——access_token 永久有效。

        上层不应调用本方法；如果 access_token 失效（用户主动撤销或卸载
        integration），应当让用户重新走 :meth:`authorize_url` 流程。

        Raises:
            NotImplementedError: 总是抛出，提示调用方走重新授权流程。
        """
        raise NotImplementedError("Notion access_token never expires")

    # ------------------------------------------------------------------
    # 4. revoke —— Basic Auth + DELETE /v1/oauth/revoke
    # ------------------------------------------------------------------
    async def revoke(self, access_token: str) -> None:
        """撤销指定的 access_token。

        Notion 的撤销接口：

            DELETE https://api.notion.com/v1/oauth/revoke
            Authorization: Basic base64(client_id:client_secret)
            Notion-Version: 2022-06-28
            Content-Type: application/json
            Body: {"token": "<access_token>"}

        撤销成功后该 token 立即失效，对应 workspace 的所有 page/database
        访问权限被回收。本方法返回 ``None``；调用方应在成功后删除本地 token 记录
        （由 P4-A 的 ``token_store`` 负责实际删库）。

        Args:
            access_token: 需要撤销的 Notion access_token。

        Raises:
            OAuthError: token 为空、credentials 未配置或接口返回 4xx。
        """
        self._ensure_credentials()
        if not access_token:
            raise OAuthError("缺少 access_token，无法撤销 Notion 授权")

        headers = {
            "Authorization": self._basic_auth_header(),
            "Content-Type": "application/json",
            **self._notion_version_header(),
        }
        await self._request_with_retry(
            "DELETE",
            REVOKE_URL,
            json_body={"token": access_token},
            headers=headers,
        )
        return None

    # ------------------------------------------------------------------
    # 5. get_user_info —— Bearer token + Notion-Version
    # ------------------------------------------------------------------
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """获取当前 access_token 对应的 bot 用户信息。

        Notion 返回字段示例（type=bot）：

            {
                "object": "user",
                "id": "...",
                "type": "bot",
                "bot": {
                    "owner": {"type": "user", "user": {...}},
                    "workspace_name": "Acme Co"
                },
                "name": "My Integration",
                "avatar_url": null
            }

        注意：Notion OAuth integration 在 ``/v1/users/me`` 拿到的是
        **bot 自身**信息（包含 workspace 名称），而不是授权用户的个人资料；
        授权用户资料需要从 :meth:`exchange_code` 返回的 ``owner`` 字段读取。

        Args:
            access_token: 来自 :meth:`exchange_code`。

        Returns:
            Notion ``/v1/users/me`` 接口的完整响应 dict。
        """
        if not access_token:
            raise OAuthError("缺少 access_token，无法获取 Notion 用户信息")

        headers = {
            "Authorization": f"Bearer {access_token}",
            **self._notion_version_header(),
        }
        return await self._request_with_retry("GET", USER_INFO_URL, headers=headers)


__all__ = ["NotionOAuthProvider"]

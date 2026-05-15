"""飞书（Lark）OAuth 2.0 Provider — P4-B 真实现。

实装了 ``BaseOAuthProvider`` 的 5 个方法，用于「安心智能助手」V3 中
对接飞书开放平台 OAuth：

    * ``authorize_url``   — 拼装授权页 URL
    * ``exchange_code``   — code → access_token / refresh_token
    * ``refresh_token``   — refresh_token 续期
    * ``revoke``          — 飞书无显式 revoke 接口，**仅做本地状态标记**
    * ``get_user_info``   — 拉取 open_id / union_id / 头像 / 邮箱等

参考文档：https://open.feishu.cn/document/server-docs/authentication-management

技术点：
    1. 完全异步（``httpx.AsyncClient``）
    2. 复用 ``core/config.py`` 的 ``FEISHU_APP_ID`` / ``FEISHU_APP_SECRET``
    3. 短超时（connect=5s, read/write=15s）
    4. 飞书错误码 ``99991663`` / ``99991664``（access_token expired）
       → :class:`OAuthTokenExpiredError`
    5. HTTP 429 限流走指数退避重试（最多 3 次）

依赖：``httpx`` （已在主包 ``requirements.txt``）。

⚠️ 文件边界：本 provider **只**使用 ``..base`` 暴露的契约，
不修改 P4-A 的任何骨架文件。
"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlencode

import httpx

from ..base import (
    BaseOAuthProvider,
    OAuthError,
    OAuthTokenBundle,
    OAuthTokenExpiredError,
)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
FEISHU_OPEN_API_BASE = "https://open.feishu.cn/open-apis"

# 授权页（用户跳转）
AUTHORIZE_URL = f"{FEISHU_OPEN_API_BASE}/authen/v1/authorize"
# v2 OAuth token 接口（同时承担 authorization_code 与 refresh_token 两种 grant）
TOKEN_URL = f"{FEISHU_OPEN_API_BASE}/authen/v2/oauth/token"
# 用户信息
USER_INFO_URL = f"{FEISHU_OPEN_API_BASE}/authen/v1/user_info"

# 飞书 access_token 失效错误码
TOKEN_EXPIRED_CODES: tuple[int, ...] = (99991663, 99991664)

# HTTP 超时（秒）
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)

# 429 限流时的最大重试次数（不含首次请求）
MAX_RETRIES_ON_RATE_LIMIT = 3


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------
class FeishuOAuthProvider(BaseOAuthProvider):
    """飞书 OAuth provider。

    ``default_scopes`` 选择理由（与 V3 智能体能力矩阵对齐）：

        * ``contact:user.id:readonly`` —
          读取用户 open_id / union_id，用于「身份打通」persona（智能助手识人）
        * ``calendar:calendar`` —
          读写用户日历，用于「日程秘书」persona（自动安排会议、提醒待办）
        * ``drive:drive`` —
          读写云空间文件，用于「文档协作」persona（拉取/上传合同、案例资料）

    更细粒度的 scope（如 ``im:message`` 用于即时通讯）由 IM Gateway 单独走
    bot token 链路（``im_gateway/feishu_adapter.py``），不混入 OAuth 流程。
    """

    provider_id = "feishu"
    display_name = "飞书"
    category = "office"
    icon_url = "https://lf-package-cn.feishucdn.com/obj/feishu-static/locale/feishu-logo.svg"
    default_scopes: list[str] = [
        "contact:user.id:readonly",
        "calendar:calendar",
        "drive:drive",
    ]

    def __init__(
        self,
        *,
        app_id: str | None = None,
        app_secret: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        redis_client: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """构造一个飞书 OAuth provider。

        优先级：注入参数 > ``core.config.settings`` 兜底。
        ``client_id``/``client_secret`` 是 BaseOAuthProvider 的标准 kwargs，
        与飞书的 ``app_id``/``app_secret`` 互为别名。

        Args:
            app_id: 飞书自建应用 App ID（飞书命名）。
            app_secret: 应用 secret（飞书命名）。
            client_id: 等价于 ``app_id``，兼容标准 OAuth 命名。
            client_secret: 等价于 ``app_secret``。
            http_client: 可注入的 ``httpx.AsyncClient``（用于测试 mock）。
            redis_client: 可选 Redis 客户端，未使用但保留以满足基类签名。
            **kwargs: 透传给基类，预留扩展。
        """
        # 标准基类构造（保存 http_client / redis_client / client_id 等）
        super().__init__(
            http_client=http_client,
            redis_client=redis_client,
            client_id=client_id or app_id,
            client_secret=client_secret or app_secret,
            **kwargs,
        )

        # 复用项目 settings；测试场景下 settings 可能不可用，做兜底
        settings_app_id = ""
        settings_app_secret = ""
        try:  # pragma: no cover - 依赖项目运行时配置
            from src.core.config import settings as _settings

            settings_app_id = getattr(_settings, "FEISHU_APP_ID", "") or ""
            settings_app_secret = getattr(_settings, "FEISHU_APP_SECRET", "") or ""
        except Exception:
            pass

        # 注入优先 → fallback 到 settings
        self._app_id: str = app_id or client_id or settings_app_id
        self._app_secret: str = app_secret or client_secret or settings_app_secret
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
        """确保 app_id / app_secret 已配置；否则抛 :class:`OAuthError`。"""
        if not self._app_id or not self._app_secret:
            raise OAuthError("飞书 OAuth 未配置：缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET")

    @staticmethod
    def _scopes_csv(scopes: list[str] | None, fallback: list[str]) -> str:
        """把 scope 列表拼成飞书要求的逗号分隔字符串。"""
        chosen = scopes if scopes else fallback
        # 去重保序
        seen: set[str] = set()
        ordered: list[str] = []
        for s in chosen:
            if s and s not in seen:
                seen.add(s)
                ordered.append(s)
        return ",".join(ordered)

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

        飞书 OAuth 接口的失败语义：
            * 网络错误 / 5xx → 指数退避重试
            * HTTP 429 → 同样指数退避重试（最多 ``MAX_RETRIES_ON_RATE_LIMIT`` 次）
            * 应用层 ``code`` ∈ ``TOKEN_EXPIRED_CODES`` → :class:`OAuthTokenExpiredError`
            * 其他 ``code != 0`` → :class:`OAuthError`

        Returns:
            解析后的 JSON dict。
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
                data = resp.json()
                code = data.get("code", 0)

                # token 失效 → 直接抛专用异常
                if code in TOKEN_EXPIRED_CODES:
                    raise OAuthTokenExpiredError(
                        message=f"飞书 access_token 已过期: code={code} msg={data.get('msg')}",
                        provider=self.provider_id,
                        code=code,
                    )

                if code != 0:
                    raise OAuthError(
                        f"飞书 OAuth API 错误: code={code} msg={data.get('msg')} url={url}"
                    )

                return data

            except httpx.HTTPStatusError as e:
                last_err = e
                # 5xx 也走重试，4xx（除 429 已上面处理）直接抛
                if e.response is not None and e.response.status_code < 500:
                    raise OAuthError(f"飞书 OAuth HTTP {e.response.status_code} 错误: {url}") from e
                if attempt >= MAX_RETRIES_ON_RATE_LIMIT:
                    break
                await asyncio.sleep(0.5 * (2**attempt))
            except httpx.TransportError as e:
                last_err = e
                if attempt >= MAX_RETRIES_ON_RATE_LIMIT:
                    break
                await asyncio.sleep(0.5 * (2**attempt))

        raise OAuthError(
            f"飞书 OAuth 调用失败（已重试 {MAX_RETRIES_ON_RATE_LIMIT} 次）: {url} → {last_err}"
        )

    # ------------------------------------------------------------------
    # 1. authorize_url —— 生成跳转授权页
    # ------------------------------------------------------------------
    async def authorize_url(
        self,
        state: str,
        redirect_uri: str,
        scopes: list[str] | None = None,
    ) -> str:
        """生成飞书 OAuth 授权页 URL。

        Args:
            state: 防 CSRF 的随机串，前端回跳时回传校验。
            redirect_uri: 飞书后台已登记的回跳地址（必须完全匹配）。
            scopes: 自定义 scope 列表；不传时使用 :attr:`default_scopes`。

        Returns:
            完整的 ``https://open.feishu.cn/open-apis/authen/v1/authorize?...`` URL。
        """
        self._ensure_credentials()

        params = {
            "app_id": self._app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": self._scopes_csv(scopes, self.default_scopes),
            "response_type": "code",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    # ------------------------------------------------------------------
    # 2. exchange_code —— code → token
    # ------------------------------------------------------------------
    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokenBundle:
        """使用授权码换取 access_token / refresh_token。

        Args:
            code: 飞书回跳带回的一次性 ``code``。
            redirect_uri: 与 :meth:`authorize_url` 中保持一致的回跳地址。

        Returns:
            :class:`OAuthTokenBundle`。

        Raises:
            OAuthError: 飞书返回非 0 业务错误码。
        """
        self._ensure_credentials()

        body = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self._app_id,
            "client_secret": self._app_secret,
            "redirect_uri": redirect_uri,
        }
        data = await self._request_with_retry(
            "POST",
            TOKEN_URL,
            json_body=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        return self._build_bundle(data)

    # ------------------------------------------------------------------
    # 3. refresh_token —— 刷新
    # ------------------------------------------------------------------
    async def refresh_token(self, refresh_token: str) -> OAuthTokenBundle:
        """使用 refresh_token 续期，返回新的 token bundle。

        飞书的 refresh_token 同样有有效期；过期会返回
        ``code in TOKEN_EXPIRED_CODES`` → 抛 :class:`OAuthTokenExpiredError`，
        上层应引导用户重新授权。
        """
        self._ensure_credentials()

        body = {
            "grant_type": "refresh_token",
            "client_id": self._app_id,
            "client_secret": self._app_secret,
            "refresh_token": refresh_token,
        }
        data = await self._request_with_retry(
            "POST",
            TOKEN_URL,
            json_body=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        return self._build_bundle(data)

    # ------------------------------------------------------------------
    # 4. revoke —— 飞书无显式 revoke
    # ------------------------------------------------------------------
    async def revoke(self, access_token: str) -> None:  # noqa: ARG002 — token 仅作日志
        """撤销授权。

        飞书开放平台**未提供**显式的 OAuth revoke 接口
        （企业管理员可在后台移除应用授权，但无单用户 token 撤销 API）。

        因此本方法**仅作本地状态标记**：调用方应在收到本方法成功返回后
        删除本地的 token 记录（由 P4-A 的 ``token_store`` 负责实际删库）。

        Note:
            如果未来飞书开放 revoke API（关注 release notes），
            在此处补一个 ``POST /authen/v1/oidc/logout`` 即可。
        """
        # 故意 no-op：让上层 token_store 删除即可。保留方法签名以满足 base 契约。
        return None

    # ------------------------------------------------------------------
    # 5. get_user_info —— 拉用户信息
    # ------------------------------------------------------------------
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """获取当前授权用户的基础信息。

        飞书返回字段示例：

            {
                "name": "张三",
                "en_name": "Zhang San",
                "avatar_url": "https://...",
                "email": "zhangsan@example.com",
                "open_id": "ou_xxx",
                "union_id": "on_xxx",
                "user_id": "xxx",
                "tenant_key": "xxx"
            }

        Args:
            access_token: 来自 :meth:`exchange_code` / :meth:`refresh_token`。

        Returns:
            飞书 ``user_info`` 接口的 ``data`` 段（dict）。
        """
        if not access_token:
            raise OAuthError("缺少 access_token，无法获取飞书用户信息")

        headers = {"Authorization": f"Bearer {access_token}"}
        data = await self._request_with_retry("GET", USER_INFO_URL, headers=headers)
        # 飞书 v1/user_info 返回 {code, msg, data: {...}}；data 可能不存在
        return data.get("data") or {}

    # ------------------------------------------------------------------
    # 内部：把飞书 token 接口的响应规整成 OAuthTokenBundle
    # ------------------------------------------------------------------
    @staticmethod
    def _build_bundle(data: dict[str, Any]) -> OAuthTokenBundle:
        """飞书 v2 token 接口的响应结构兼容（``data`` 段可能存在也可能扁平）。"""
        # 一些 v2 接口直接返回扁平字段，少数返回 {code, data: {...}}
        payload = data.get("data") if isinstance(data.get("data"), dict) else data
        access_token = payload.get("access_token") or ""
        if not access_token:
            raise OAuthError(f"飞书 token 响应缺少 access_token: {data!r}")
        return OAuthTokenBundle(
            access_token=access_token,
            refresh_token=payload.get("refresh_token"),
            expires_in=int(payload["expires_in"]) if payload.get("expires_in") else None,
            scope=payload.get("scope"),
            token_type=payload.get("token_type", "Bearer"),
            raw=data,
        )


__all__ = ["FeishuOAuthProvider"]

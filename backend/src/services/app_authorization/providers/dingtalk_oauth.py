"""钉钉 OAuth 2.0 Provider（P4-C）。

参考文档：
- https://open.dingtalk.com/document/orgapp/obtain-identity-credentials
- https://open.dingtalk.com/document/orgapp/obtain-user-token

接口对齐 P4-A 框架（``BaseOAuthProvider`` / ``OAuthTokenBundle``），与飞书
OAuth Provider（P4-B）的差异点：

1. **token 端点**：钉钉用 ``POST https://api.dingtalk.com/v1.0/oauth2/userAccessToken``，
   字段命名为 ``clientId / clientSecret / refreshToken / grantType``（驼峰，
   且 ``grantType`` 用 ``authorization_code`` / ``refresh_token``）；
   飞书用 ``app_id / app_secret``（蛇形）。
2. **用户信息鉴权头**：钉钉使用自定义头
   ``x-acs-dingtalk-access-token: <accessToken>``，**不**走 ``Authorization: Bearer``；
   飞书走 OAuth 标准的 ``Authorization: Bearer``。
3. **撤销接口**：钉钉**没有**官方 revoke 端点，只能本地标记 revoked；
   飞书有 ``/authen/v1/oidc/access_token`` 反向操作。
4. **scope 编码**：钉钉文档示例使用空格分隔的 scope 列表（如
   ``openid Contact.User.Read``），并以 ``prompt=consent`` 强制每次确认。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from loguru import logger

# ---------------------------------------------------------------------------
# Base 类导入：优先用 P4-A 框架，缺失时本地 fallback
# ---------------------------------------------------------------------------
try:  # pragma: no cover - 仅在 P4-A base 已合入时走真实路径
    from ..base import BaseOAuthProvider, OAuthTokenBundle  # type: ignore
except ImportError:  # pragma: no cover - 测试 / 框架未合入时使用 fallback
    from dataclasses import dataclass, field

    @dataclass
    class OAuthTokenBundle:  # type: ignore[no-redef]
        """OAuth token 三元组的标准化封装。

        ``expires_at`` 为 UTC，**含时区**。所有 Provider 必须返回该结构，
        让上层 ``AppAuthorizationService`` 能统一刷新与持久化。
        """

        access_token: str
        refresh_token: str | None = None
        expires_at: datetime | None = None
        scope: str | None = None
        token_type: str = "Bearer"
        raw: dict[str, Any] = field(default_factory=dict)

    class BaseOAuthProvider:  # type: ignore[no-redef]
        """OAuth Provider 抽象基类（fallback 版本）。

        子类必须覆盖类属性 ``provider_id`` / ``display_name`` / ``category``
        / ``icon_url`` / ``default_scopes``，并实装 5 个异步方法。
        """

        provider_id: str = ""
        display_name: str = ""
        category: str = ""
        icon_url: str = ""
        default_scopes: list[str] = []

        def __init__(
            self,
            *,
            client_id: str,
            client_secret: str,
            redirect_uri: str,
            http_client: httpx.AsyncClient | None = None,
        ) -> None:
            self.client_id = client_id
            self.client_secret = client_secret
            self.redirect_uri = redirect_uri
            self._http = http_client


# ---------------------------------------------------------------------------
# 钉钉 OAuth Provider 实装
# ---------------------------------------------------------------------------
class DingTalkOAuthProvider(BaseOAuthProvider):
    """钉钉企业内部应用 / 第三方企业应用 OAuth 2.0。

    使用方式::

        provider = DingTalkOAuthProvider(
            client_id=settings.DINGTALK_APP_KEY,
            client_secret=settings.DINGTALK_APP_SECRET,
            redirect_uri="https://anxin.example/oauth/callback/dingtalk",
        )
        url = await provider.authorize_url(state="xyz")
        bundle = await provider.exchange_code(code, state="xyz")
        user = await provider.get_user_info(bundle.access_token)
    """

    # ---- Provider 元数据（被 ``providers/registry.py`` 反射使用） ----
    provider_id = "dingtalk"
    display_name = "钉钉"
    category = "office"
    # 钉钉公开 logo CDN（阿里云 OSS）
    icon_url = (
        "https://gw.alicdn.com/imgextra/i4/O1CN01"
        "JlhuIB1BgsBhpdSor_!!6000000000005-2-tps-128-128.png"
    )
    # openid     — 必填，标识用户
    # Contact.User.Read — 读取通讯录用户档案
    # Calendar.Read    — 读取日历（用于安排日程类智能体）
    default_scopes = ["openid", "Contact.User.Read", "Calendar.Read"]

    # ---- 钉钉 OAuth 端点常量 ----
    AUTHORIZE_URL = "https://login.dingtalk.com/oauth2/auth"
    TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
    USERINFO_URL = "https://api.dingtalk.com/v1.0/contact/users/me"

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        redis_client: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """构造钉钉 OAuth provider。

        优先级：注入参数 > ``core.config.settings`` 兜底。

        Args:
            client_id: 钉钉 ``AppKey``；缺省读取 ``settings.DINGTALK_APP_KEY``。
            client_secret: 钉钉 ``AppSecret``；缺省读取
                ``settings.DINGTALK_APP_SECRET``。
            redirect_uri: 回跳 URL（必须在钉钉控制台白名单内）。
            http_client: 可注入的 ``httpx.AsyncClient``，用于测试 mock。
            redis_client: 可选 Redis 客户端，保留以满足基类签名。
            **kwargs: 透传给基类。
        """
        # 注入优先 → fallback 到 settings
        settings_client_id = ""
        settings_client_secret = ""
        settings_redirect = ""
        try:  # pragma: no cover - 运行期 settings 可能不可用
            from src.core.config import settings as _settings

            settings_client_id = getattr(_settings, "DINGTALK_APP_KEY", "") or ""
            settings_client_secret = getattr(_settings, "DINGTALK_APP_SECRET", "") or ""
            settings_redirect = getattr(_settings, "DINGTALK_OAUTH_REDIRECT_URI", "") or ""
        except Exception:
            pass

        resolved_client_id = client_id or settings_client_id
        resolved_client_secret = client_secret or settings_client_secret
        resolved_redirect = redirect_uri or settings_redirect

        super().__init__(
            http_client=http_client,
            redis_client=redis_client,
            client_id=resolved_client_id,
            client_secret=resolved_client_secret,
            redirect_uri=resolved_redirect,
            **kwargs,
        )

    # ============== 1. 授权 URL ==============
    async def authorize_url(
        self,
        state: str,
        *,
        scopes: list[str] | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        """生成钉钉授权页 URL。

        钉钉 scope 用空格分隔（``openid Contact.User.Read``），并附加
        ``prompt=consent`` 强制每次显式同意，避免静默续签导致用户感知不到。
        """
        scope_list = scopes or self.default_scopes
        params: dict[str, str] = {
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "client_id": self.client_id,
            "scope": " ".join(scope_list),
            "state": state,
            "prompt": "consent",
        }
        if extra_params:
            params.update(extra_params)
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    # ============== 2. code → token ==============
    async def exchange_code(
        self,
        code: str,
        *,
        state: str | None = None,  # noqa: ARG002 — 兼容签名，钉钉换 token 不传 state
    ) -> OAuthTokenBundle:
        """用授权码换取 ``accessToken`` / ``refreshToken``。"""
        body = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "code": code,
            "grantType": "authorization_code",
        }
        data = await self._post_json(self.TOKEN_URL, body)
        return self._bundle_from_response(data)

    # ============== 3. 刷新 token ==============
    async def refresh_token(
        self,
        refresh_token: str,
    ) -> OAuthTokenBundle:
        """用 refresh_token 换取新的 access_token。

        钉钉与换 token 共用同一端点，仅 grantType 不同。
        """
        body = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "refreshToken": refresh_token,
            "grantType": "refresh_token",
        }
        data = await self._post_json(self.TOKEN_URL, body)
        bundle = self._bundle_from_response(data)
        # 钉钉刷新接口若未返回新 refresh_token，沿用旧的，避免下次刷新失败
        if not bundle.refresh_token:
            bundle.refresh_token = refresh_token
        return bundle

    # ============== 4. 撤销 ==============
    async def revoke(self, access_token: str) -> None:  # noqa: ARG002
        """钉钉无 revoke 端点。

        本方法仅打印日志，由上层服务在数据库中把绑定标记为 ``revoked`` 即可。
        """
        logger.info("[dingtalk_oauth] 钉钉无远端 revoke 接口，仅本地标记为 revoked")
        return None

    # ============== 5. 用户信息 ==============
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """拉取当前登录用户的档案。

        钉钉使用自定义头 ``x-acs-dingtalk-access-token``（**不是** OAuth 标准
        ``Authorization: Bearer``），上层调用方必须直接传 ``access_token``。
        """
        headers = {"x-acs-dingtalk-access-token": access_token}
        client = self._client()
        owns_client = self._http is None
        try:
            resp = await client.get(self.USERINFO_URL, headers=headers)
            self._raise_for_dingtalk_error(resp)
            return resp.json()
        finally:
            if owns_client:
                await client.aclose()

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _client(self) -> httpx.AsyncClient:
        """返回 httpx client：测试可注入，生产临时创建。"""
        if self._http is not None:
            return self._http
        return httpx.AsyncClient(timeout=10.0)

    async def _post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        owns_client = self._http is None
        try:
            resp = await client.post(url, json=body)
            self._raise_for_dingtalk_error(resp)
            return resp.json()
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _raise_for_dingtalk_error(resp: httpx.Response) -> None:
        """钉钉错误体格式：``{"code": "...", "message": "...", "requestid": "..."}``。

        2xx + 无 ``code`` 字段视为成功；4xx/5xx 或含 ``code`` 字段抛 ``ValueError``。
        """
        if resp.status_code >= 400:
            try:
                data = resp.json()
            except Exception:  # noqa: BLE001
                data = {"raw": resp.text}
            logger.error(f"[dingtalk_oauth] HTTP {resp.status_code} {data}")
            raise ValueError(
                f"钉钉 OAuth 请求失败: HTTP {resp.status_code} - "
                f"{data.get('message') or data.get('raw', '未知错误')}"
            )

    @staticmethod
    def _bundle_from_response(data: dict[str, Any]) -> OAuthTokenBundle:
        """把钉钉响应映射到 ``OAuthTokenBundle``。

        响应字段（驼峰）::

            {
              "accessToken":  "ey...",
              "refreshToken": "rt-...",
              "expireIn":     7200,
              "corpId":       "dingxxx"
            }
        """
        access = data.get("accessToken") or data.get("access_token")
        if not access:
            raise ValueError(f"钉钉返回缺少 accessToken 字段: {data}")
        refresh = data.get("refreshToken") or data.get("refresh_token")
        expire_in = data.get("expireIn") or data.get("expire_in")
        expires_at: datetime | None = None
        if isinstance(expire_in, (int, float)):
            expires_at = datetime.now(UTC) + timedelta(
                seconds=int(expire_in) - 60  # 提前 60s 视为过期，避免边界
            )
        return OAuthTokenBundle(
            access_token=access,
            refresh_token=refresh,
            expires_at=expires_at,
            scope=data.get("scope"),
            token_type="Bearer",
            raw=data,
        )

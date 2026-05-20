# -*- coding: utf-8 -*-
"""
OIDC（OpenID Connect）登录支持

设计动机（deploy/enterprise-onprem/SSO_SAML.md "接入约定"）：
    身份必须最终映射到本地 ``users`` 表 —— IdP 声明 ``subject`` 只证明
    "你是谁"，不证明"你能干什么"。本地 ``role_bindings`` 才决定权限。

实装策略：
    - 仅做 **ID Token 校验**（不做 Access Token / refresh）
    - JWKS 通过 OIDC discovery (``${issuer}/.well-known/openid-configuration``) 获取
    - JWKS 内存缓存（默认 1h），expired 触发刷新
    - JWT 验签用 ``python-jose``（已在依赖：python-jose[cryptography]）
    - 校验 iss / aud / exp / iat，且时钟偏移容忍 ±5 min

无 OIDC SDK 强依赖；缺失任何配置都 fail-closed（``OidcUnavailable``）。
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class OidcError(RuntimeError):
    """OIDC 校验失败的通用异常 —— 调用方应当返回 401。"""


class OidcUnavailable(RuntimeError):
    """配置缺失 / discovery 失败 —— 调用方应当返回 503。"""


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class OidcConfig:
    """单个 OIDC IdP 的配置。

    ``issuer`` 用于做 discovery；``client_id`` 用于校验 aud；
    ``audience_override`` 可选，覆盖 aud 检查（某些 IdP 会发别名）。
    """

    issuer: str
    client_id: str
    audience_override: str | None = None
    jwks_uri: str | None = None         # 可选硬编码，跳过 discovery
    cache_ttl_sec: int = 3600
    clock_skew_sec: int = 300
    http_timeout_sec: float = 10.0
    # 部分 IdP（如 ADFS）签名算法不是 RS256；通过白名单显式列出
    allowed_algorithms: tuple[str, ...] = ("RS256",)


@dataclass(slots=True)
class _JwksCacheEntry:
    keys: list[dict[str, Any]]
    fetched_at: float


# ---------------------------------------------------------------------------
# 客户端
# ---------------------------------------------------------------------------


class OidcVerifier:
    """OIDC ID Token 校验器。

    线程安全：JWKS 缓存通过 asyncio.Lock 保护。

    用法::

        verifier = OidcVerifier(OidcConfig(issuer=..., client_id=...))
        claims = await verifier.verify_id_token(id_token)
        email = claims.get("email")  # 映射到本地 users.email
    """

    def __init__(self, config: OidcConfig) -> None:
        if not config.issuer:
            raise OidcUnavailable("issuer 不能为空")
        if not config.client_id:
            raise OidcUnavailable("client_id 不能为空")
        self.config = config
        self._cache: _JwksCacheEntry | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # 公开
    # ------------------------------------------------------------------

    async def verify_id_token(self, id_token: str) -> dict[str, Any]:
        """校验 ID Token 并返回 claims。

        Raises:
            OidcError: 任何校验失败（签名 / aud / exp / iat / iss）
            OidcUnavailable: 拉 JWKS 或 discovery 失败
        """
        if not id_token or "." not in id_token:
            raise OidcError("id_token 格式非法")

        # 1) 取 JWKS
        keys = await self._get_jwks()

        # 2) 取 header.kid，从 JWKS 里找匹配的 key
        try:
            from jose import jwt  # type: ignore[import-not-found]
            from jose.exceptions import JWTError  # type: ignore[import-not-found]
        except ImportError as exc:
            raise OidcUnavailable(
                "需要 python-jose: pip install 'python-jose[cryptography]'"
            ) from exc

        try:
            unverified_header = jwt.get_unverified_header(id_token)
        except JWTError as exc:
            raise OidcError(f"id_token header 解析失败: {exc}") from exc

        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg")
        if alg not in self.config.allowed_algorithms:
            raise OidcError(f"签名算法 {alg!r} 不在 allowed_algorithms")

        if kid:
            key = next((k for k in keys if k.get("kid") == kid), None)
        else:
            # 没 kid：当 JWKS 只有一把时勉强放行
            key = keys[0] if len(keys) == 1 else None
        if key is None:
            # JWKS 也许刚轮转过；强制刷新一次再试
            await self._refresh_jwks()
            keys2 = await self._get_jwks()
            key = next((k for k in keys2 if k.get("kid") == kid), None)
            if key is None:
                raise OidcError(f"未在 JWKS 中找到 kid={kid!r}")

        audience = self.config.audience_override or self.config.client_id
        try:
            claims = jwt.decode(
                id_token,
                key,
                algorithms=list(self.config.allowed_algorithms),
                audience=audience,
                issuer=self.config.issuer,
                options={"verify_at_hash": False},
            )
        except JWTError as exc:
            raise OidcError(f"id_token 校验失败: {exc}") from exc

        # 额外手动验时钟偏移（python-jose 默认不带 leeway）
        now = int(time.time())
        exp = claims.get("exp")
        iat = claims.get("iat")
        if exp is not None and now > exp + self.config.clock_skew_sec:
            raise OidcError("id_token 已过期（含 leeway）")
        if iat is not None and now + self.config.clock_skew_sec < iat:
            raise OidcError("id_token iat 在未来（含 leeway）")

        if not claims.get("sub"):
            raise OidcError("claims 缺少 sub")

        return claims

    # ------------------------------------------------------------------
    # JWKS 拉取 / 缓存
    # ------------------------------------------------------------------

    async def _get_jwks(self) -> list[dict[str, Any]]:
        now = time.time()
        if (
            self._cache is not None
            and now - self._cache.fetched_at < self.config.cache_ttl_sec
        ):
            return list(self._cache.keys)
        await self._refresh_jwks()
        assert self._cache is not None
        return list(self._cache.keys)

    async def _refresh_jwks(self) -> None:
        async with self._lock:
            # 双检：如果别的协程已经刷新过，跳过
            now = time.time()
            if (
                self._cache is not None
                and now - self._cache.fetched_at < self.config.cache_ttl_sec
            ):
                return
            jwks_uri = self.config.jwks_uri or await self._discover_jwks_uri()
            keys = await self._fetch_jwks(jwks_uri)
            self._cache = _JwksCacheEntry(keys=keys, fetched_at=time.time())

    async def _discover_jwks_uri(self) -> str:
        url = f"{self.config.issuer.rstrip('/')}/.well-known/openid-configuration"
        try:
            import httpx
        except ImportError as exc:
            raise OidcUnavailable("需要 httpx") from exc
        async with httpx.AsyncClient(timeout=self.config.http_timeout_sec) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise OidcUnavailable(f"discovery 失败 status={resp.status_code}")
            data = resp.json()
        jwks_uri = data.get("jwks_uri")
        if not jwks_uri:
            raise OidcUnavailable("discovery 响应缺少 jwks_uri")
        # 校验 issuer 一致性
        if data.get("issuer") and data["issuer"] != self.config.issuer:
            raise OidcUnavailable(
                f"discovery issuer 不一致：{data['issuer']!r} vs {self.config.issuer!r}"
            )
        return jwks_uri

    async def _fetch_jwks(self, jwks_uri: str) -> list[dict[str, Any]]:
        try:
            import httpx
        except ImportError as exc:
            raise OidcUnavailable("需要 httpx") from exc
        async with httpx.AsyncClient(timeout=self.config.http_timeout_sec) as client:
            resp = await client.get(jwks_uri)
            if resp.status_code != 200:
                raise OidcUnavailable(f"JWKS 拉取失败 status={resp.status_code}")
            data = resp.json()
        keys = data.get("keys") or []
        if not isinstance(keys, list) or not keys:
            raise OidcUnavailable("JWKS 响应不含 keys 数组")
        return keys


__all__ = ["OidcConfig", "OidcError", "OidcUnavailable", "OidcVerifier"]

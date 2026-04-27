# -*- coding: utf-8 -*-
"""
OAuth Provider 抽象基类（P4-A）

所有第三方应用授权 provider（飞书 / 钉钉 / Notion / Shopify / GitHub / 阿里云 …）
必须继承 ``BaseOAuthProvider``，实现统一的 5 个方法 + 4 个 ClassVar 元数据。

设计目标
--------
- 上层业务（OAuthFlowService / API 路由）只依赖抽象接口，不关心具体平台 SDK；
- 通过 ``OAuthProviderRegistry`` 按 ``provider_id`` 路由到具体实现；
- 元数据（display_name / category / icon_url / default_scopes）暴露给前端
  应用市场页，无需查询任何远端服务。

接口契约对所有 P4-B/C/D/E provider agent 强约束 —— 字段名 / 返回类型 /
方法签名严禁修改，否则 OAuthFlowService 调用链会全面失败。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar


# ---------------------------------------------------------------------------
# OAuth provider 异常族（P8-A 补齐）
# ---------------------------------------------------------------------------
# P4-B/C/D/E 各 provider（feishu / dingtalk / notion / shopify ...）从
# ``..base`` import 这两个异常类型；P4-A 框架只定义了 ``OAuthFlowError`` 系列
# 在 ``oauth_flow`` 中，未在 base 暴露 provider 侧的异常基类，
# 导致所有 provider import 即崩。这里补齐：
#   - ``OAuthError``                : provider 侧通用错误基类
#   - ``OAuthTokenExpiredError``    : token 过期 / 失效（需要重新授权或刷新）
class OAuthError(Exception):
    """OAuth provider 调用通用异常基类。

    所有 provider 在配置缺失 / 凭据无效 / 远端非 2xx / 解析失败等场景应抛该异常
    或其子类；上层 ``OAuthFlowService`` 会再包装为 :class:`OAuthProviderError`。
    """


class OAuthTokenExpiredError(OAuthError):
    """OAuth access_token / refresh_token 过期或被撤销。

    Provider 检测到「token 已失效」（如飞书 ``code in TOKEN_EXPIRED_CODES``、
    Notion 401、Shopify 401 等）时抛出，让上层进入 refresh / re-auth 流程。
    """


@dataclass
class OAuthTokenBundle:
    """OAuth 2.0 token 三元组（access + refresh + 元数据）。

    所有 provider 在 ``exchange_code`` / ``refresh_token`` 后必须返回该结构。
    """

    #: 访问令牌（必填）
    access_token: str
    #: 刷新令牌（不是所有 provider 都返回，如 Slack 默认无 refresh）
    refresh_token: str | None = None
    #: token 类型，通常是 "Bearer"
    token_type: str = "Bearer"
    #: token 过期绝对时间（UTC）；None 表示长期有效
    expires_at: datetime | None = None
    #: 实际授予的 scope 列表（可能与 default_scopes 不同）
    scopes: list[str] = field(default_factory=list)
    #: 平台原始响应（保留以备调试 / 平台特有字段）
    raw: dict = field(default_factory=dict)


class BaseOAuthProvider(ABC):
    """OAuth Provider 抽象基类。

    子类必须设置以下 4 个 ClassVar：
        - ``provider_id``    : 全小写 snake_case，作为路由 key（如 "feishu"）
        - ``display_name``   : 应用市场卡片标题（如 "飞书"）
        - ``category``       : 应用类别（office | ecommerce | content | crm |
                                design | info_source | compliance）
        - ``default_scopes`` : 默认请求的权限列表

    并实现 5 个抽象方法：
        - ``authorize_url``  : 拼接授权 URL
        - ``exchange_code``  : code → token
        - ``refresh_token``  : refresh_token → new token bundle
        - ``revoke``         : 主动注销 token
        - ``get_user_info``  : 拉取用户信息（用于绑定展示）
    """

    #: provider 唯一标识（全小写 snake_case），路由 key
    provider_id: ClassVar[str]
    #: 应用市场展示名（中文/英文均可）
    display_name: ClassVar[str]
    #: 应用类别（前端按类别分组展示）
    category: ClassVar[str]
    #: 应用图标 URL（可空，缺省时前端用首字母）
    icon_url: ClassVar[str | None] = None
    #: 默认 scope 列表
    default_scopes: ClassVar[list[str]] = []

    # ------------------------------------------------------------------
    # 抽象接口
    # ------------------------------------------------------------------
    @abstractmethod
    async def authorize_url(
        self,
        state: str,
        redirect_uri: str,
        scopes: list[str] | None = None,
    ) -> str:
        """生成第三方授权页 URL（用户跳转目标）。

        参数
        ----
        state : str
            CSRF 防御随机串，由 ``OAuthFlowService.start`` 生成并落 Redis。
        redirect_uri : str
            授权完成后的回调地址，需提前在 provider 控制台白名单。
        scopes : list[str] | None
            本次请求的权限，None 时使用 ``default_scopes``。

        返回
        ----
        完整的授权 URL（含 client_id / state / scope / response_type 等）。
        """
        raise NotImplementedError

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokenBundle:
        """用授权码（code）换取 token bundle。"""
        raise NotImplementedError

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> OAuthTokenBundle:
        """用 refresh_token 续期，返回新的 token bundle。

        若 provider 不支持刷新（如 Slack），实现可直接 raise NotImplementedError。
        """
        raise NotImplementedError

    @abstractmethod
    async def revoke(self, access_token: str) -> None:
        """主动撤销授权。"""
        raise NotImplementedError

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict:
        """获取授权用户信息（用于在前端展示绑定身份）。

        建议返回字段：``{"id": "...", "name": "...", "email": "...", "raw": {...}}``。
        """
        raise NotImplementedError

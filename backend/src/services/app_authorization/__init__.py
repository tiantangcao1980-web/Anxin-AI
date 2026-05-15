"""
App Authorization 模块（P4-A）

通用 OAuth 2.0 授权码流程框架，统一接入第三方应用（飞书 / 钉钉 /
Notion / Shopify / GitHub / 阿里云 / 设计平台 / 信息源 / 合规系统 ...）。

主要导出
--------
- ``BaseOAuthProvider`` / ``OAuthTokenBundle`` : 抽象接口
- ``OAuthProviderRegistry`` / ``register_provider`` : 注册表 + 装饰器
- ``OAuthFlowService`` : start / callback / refresh / disconnect 编排
- ``TokenStore`` : Fernet 加密 token 持久化
- ``AppAuthorization`` / ``AppToken`` / ``AppAuthorizationStatus`` : ORM
"""

from src.services.app_authorization.base import (
    BaseOAuthProvider,
    OAuthTokenBundle,
)
from src.services.app_authorization.models import (
    AppAuthorization,
    AppAuthorizationStatus,
    AppToken,
)
from src.services.app_authorization.oauth_flow import (
    OAuthFlowError,
    OAuthFlowService,
    OAuthNotFoundError,
    OAuthProviderError,
    OAuthStateError,
)
from src.services.app_authorization.registry import (
    OAuthProviderRegistry,
    register_provider,
)
from src.services.app_authorization.token_store import (
    TokenStore,
    TokenStoreConfigError,
)

__all__ = [
    # base
    "BaseOAuthProvider",
    "OAuthTokenBundle",
    # registry
    "OAuthProviderRegistry",
    "register_provider",
    # flow
    "OAuthFlowService",
    "OAuthFlowError",
    "OAuthStateError",
    "OAuthProviderError",
    "OAuthNotFoundError",
    # token store
    "TokenStore",
    "TokenStoreConfigError",
    # models
    "AppAuthorization",
    "AppAuthorizationStatus",
    "AppToken",
]

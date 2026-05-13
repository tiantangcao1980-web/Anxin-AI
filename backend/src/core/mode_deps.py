"""
V2 三态运行模式 + 订阅功能守卫依赖

提供两个 FastAPI 依赖工厂：
- require_mode(allow=[...])：检查 X-Privacy-Mode 头 + 订阅 allowed_modes
- require_subscription_feature(feature_key)：检查订阅是否包含某 feature

设计原则：
- fail-safe：老客户端不传 X-Privacy-Mode 头时，按订阅 allowed_modes[0] 推断
- super_admin 跳过：is_superuser=True 用户可绕过两个守卫，方便后台调试
- client_type 自动推断：按 user.primary_client 决定查 needer 还是 provider 套餐

参考：
- 任务 TASK-09 P0-1（docs/audit/_tasks/task-09-risk-investigation.md）
- 调研提案（docs/audit/09-risk/PROPOSAL-mode-guard.md）
"""

from collections.abc import Awaitable, Callable, Iterable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.subscription_service import SubscriptionService

VALID_MODES = {"local", "hybrid", "cloud"}


def _infer_client_type(user: User) -> str:
    """按 user.primary_client 推断订阅 client_type；老用户字段为空时回退 needer"""
    primary = getattr(user, "primary_client", None) or "needer"
    return primary if primary in {"needer", "provider"} else "needer"


def _is_superuser(user: User) -> bool:
    return bool(getattr(user, "is_superuser", False))


def require_mode(allow: Iterable[str]) -> Callable[..., Awaitable[User]]:
    """
    模式守卫工厂。

    用法：
        @router.post("/company")
        async def investigate_company(
            user: User = Depends(require_mode(["hybrid", "cloud"])),
            ...
        ):
            ...

    行为：
        1. 超级管理员直接放行（便于后台调试 + 测试）
        2. 读取请求头 X-Privacy-Mode：
            - 合法值（local/hybrid/cloud）：直接使用
            - 非法 / 缺失：按订阅 allowed_modes[0] 推断（老客户端兼容）
        3. 推断后的 mode 不在 allow 列表 → 403
        4. 订阅不允许该 mode → 402（前端可据此跳订阅升级页）
    """
    allow_set = {m.lower() for m in allow}
    if not allow_set <= VALID_MODES:
        raise ValueError(f"require_mode allow 列表包含非法值: {allow_set - VALID_MODES}")

    async def dep(
        request: Request,
        user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if _is_superuser(user):
            return user

        client_type = _infer_client_type(user)
        svc = SubscriptionService(db)

        header_mode = (request.headers.get("X-Privacy-Mode") or "").lower()
        if header_mode not in VALID_MODES:
            features = await svc.get_effective_features(user.id, client_type)
            modes = [m.lower() for m in features.get("modes", ["local"])]
            header_mode = modes[0] if modes else "local"

        if header_mode not in allow_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"该功能不支持 {header_mode} 模式，请在前端切换到 {'/'.join(sorted(allow_set))} 模式",
            )

        if not await svc.can_use_mode(user.id, header_mode, client_type):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"当前订阅不允许 {header_mode} 模式，请升级订阅",
            )

        return user

    return dep


def require_subscription_feature(feature_key: str) -> Callable[..., Awaitable[User]]:
    """
    订阅功能守卫工厂。

    用法：
        @router.post("/company")
        async def investigate_company(
            _: User = Depends(require_subscription_feature("due_diligence")),
            ...
        ):
            ...

    行为：
        1. 超级管理员直接放行
        2. SubscriptionService.can_access_feature(user_id, feature_key) 返回 False → 402
    """

    async def dep(
        user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if _is_superuser(user):
            return user

        client_type = _infer_client_type(user)
        svc = SubscriptionService(db)
        if not await svc.can_access_feature(user.id, feature_key, client_type):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"该功能（{feature_key}）需要订阅升级",
            )
        return user

    return dep

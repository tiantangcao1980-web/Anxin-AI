# -*- coding: utf-8 -*-
"""
FastAPI Dependencies —— PEP 第一层

把 PDP（`authz.decide`）封装成 FastAPI dependency，业务路由用：

    @router.post("/contracts/review")
    async def review_contract(
        body: ReviewRequest,
        _gate: None = Depends(require_scope("skill.contract.review")),
    ):
        ...

dependency 内部会从 `current_user` 推 subject，从 request 推 context，
从 path / body 推 resource。失败抛 HTTPException 403。
"""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from loguru import logger

from src.core.deps import get_current_user
from src.models.user import User
from src.services.governance import audit
from src.services.governance.authz import Decision, decide


def _subject_from_user(user: User) -> dict:
    return {
        "id": str(getattr(user, "id", "anon")),
        "role": getattr(user, "role", "guest"),
        "tenant_id": getattr(user, "tenant_id", "unknown"),
        "clearance": getattr(user, "clearance", "L2"),
        "primary_jurisdiction": getattr(user, "primary_jurisdiction", "CN"),
    }


def _context_from_request(request: Request) -> dict:
    headers = request.headers
    return {
        "ip": request.client.host if request.client else "",
        "user_agent": headers.get("user-agent", ""),
        "mfa_recent": headers.get("x-mfa-recent", "false").lower() == "true",
        "device_trust": headers.get("x-device-trust", "byod"),
        "business_hours": True,    # 由前端 / 网关注入
    }


def require_scope(
    action: str,
    *,
    resource_factory: Callable[[Request], dict] | None = None,
) -> Callable:
    """生成一个 FastAPI dependency 用于守门。

    `action` = 完整 scope 字符串，如 ``skill.contract.review``。
    `resource_factory(request) -> resource_dict` 可自定义；默认从路径推。
    """
    async def dep(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> None:
        subject = _subject_from_user(current_user)
        context = _context_from_request(request)
        if resource_factory:
            resource = resource_factory(request)
        else:
            resource = {
                "type": action.split(".")[0],
                "id": request.url.path,
                "classification": "L2",       # 调用方应通过 resource_factory 显式指定
                "jurisdiction": "CN",
            }
        res = decide(subject=subject, action=action, resource=resource, context=context)
        audit.write_event({
            "event_type": "authz.decide",
            "actor": subject,
            "action": action,
            "resource": resource,
            "decision": res.decision.value,
            "decision_reasons": res.reasons,
            "policy_snapshot_id": res.policy_snapshot_id,
            "context": context,
        })
        if res.decision == Decision.DENY:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail={
                "code": "AUTHZ_DENY",
                "action": action,
                "reasons": res.reasons,
            })
        if res.decision == Decision.REQUIRE_STEP_UP:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={
                "code": "AUTHZ_STEP_UP_REQUIRED",
                "action": action,
                "reasons": res.reasons,
            })
        if res.decision == Decision.REQUIRE_CONFIRM:
            # 由路由侧拦截后转入"草稿 + push to inbox"流程；这里仅注入 header 提示
            request.state.require_confirm = True
            request.state.confirm_action = action
            return
        # ALLOW
        return

    return dep


__all__ = ["require_scope"]

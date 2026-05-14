# -*- coding: utf-8 -*-
"""
/api/v1/skill-sandbox/quota/* —— Skills 沙箱配额管理

设计动机：让 ORG_ADMIN / super_admin 通过后台 UI 查看 / 设置每租户每 tier 的
calls_per_day / compute_ms_per_day / concurrent_executions 上限。

存储策略：
    - **进程内单例**：本期把 spec + usage 放在 ``InMemoryQuotaTracker``，K8s 多 worker
      场景下应替换为 ``RedisQuotaTracker`` 单例。
    - **持久化**：本期不入 DB；重启后 spec 恢复默认。生产 P+1 阶段把 spec
      入 ``Subscription`` 表，由 billing service 触发同步。

权限：
    - 列出 / 更新 spec：``MANAGE_SUBSCRIPTIONS``
    - 查看自己的 usage：登录用户即可（自己租户）
    - 查看他人 usage：``MANAGE_SUBSCRIPTIONS``
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.core.deps import (
    Permission,
    get_current_user_required,
    require_permission,
)
from src.models.user import User
from src.services.skill_sandbox import (
    InMemoryQuotaTracker,
    QuotaSpec,
    SandboxTier,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 单例 tracker —— 与 SkillSandboxRunner 共享，否则数据对不上
# ---------------------------------------------------------------------------


_SHARED_TRACKER: InMemoryQuotaTracker | None = None


def get_shared_tracker() -> InMemoryQuotaTracker:
    """模块级单例。

    SkillSandboxRunner 默认构造时也用 InMemoryQuotaTracker；为了让 UI 查询
    到的 usage 和实际 runner 写入的一致，必须复用同一个实例。
    生产应替换为 ``RedisQuotaTracker``：参见 docs/v3/skills-sandbox-design.md §10。
    """
    global _SHARED_TRACKER
    if _SHARED_TRACKER is None:
        _SHARED_TRACKER = InMemoryQuotaTracker()
    return _SHARED_TRACKER


# ---------------------------------------------------------------------------
# I/O 模型
# ---------------------------------------------------------------------------


TierName = Literal["T0", "T1", "T2", "T3", "T4"]


class QuotaSpecOut(BaseModel):
    tier: TierName
    calls_per_day: int | None
    compute_ms_per_day: int | None
    concurrent_executions: int | None


class QuotaSpecUpdate(BaseModel):
    """全字段可选；省略字段表示"不限"。"""

    calls_per_day: int | None = Field(default=None, ge=0)
    compute_ms_per_day: int | None = Field(default=None, ge=0)
    concurrent_executions: int | None = Field(default=None, ge=0)


class QuotaUsageOut(BaseModel):
    tier: TierName
    period_key: str
    calls: int
    compute_ms: int
    in_flight: int
    spec: QuotaSpecOut


class QuotaSnapshotOut(BaseModel):
    tenant_id: str
    tiers: list[QuotaUsageOut]


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------


@router.get(
    "/tenants/{tenant_id}",
    response_model=QuotaSnapshotOut,
)
async def get_quota_snapshot(
    tenant_id: str,
    user: User = Depends(get_current_user_required),
) -> QuotaSnapshotOut:
    """读取某租户当前周期内的全 tier 配额 / 使用快照。

    权限：自己租户 → 自由查；他人租户 → 需要 MANAGE_SUBSCRIPTIONS。
    """
    if tenant_id != (user.org_id or ""):
        from src.core.deps import has_permission
        if not has_permission(user.role, Permission.MANAGE_SUBSCRIPTIONS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查询其他租户配额",
            )

    tracker = get_shared_tracker()
    out: list[QuotaUsageOut] = []
    for tier in SandboxTier:
        usage = tracker.snapshot(tenant_id, tier)
        spec = tracker.get_spec(tenant_id=tenant_id, tier=tier)
        out.append(
            QuotaUsageOut(
                tier=tier.value,  # type: ignore[arg-type]
                period_key=usage.period_key,
                calls=usage.calls,
                compute_ms=usage.compute_ms,
                in_flight=usage.in_flight,
                spec=QuotaSpecOut(
                    tier=tier.value,  # type: ignore[arg-type]
                    calls_per_day=spec.calls_per_day,
                    compute_ms_per_day=spec.compute_ms_per_day,
                    concurrent_executions=spec.concurrent_executions,
                ),
            )
        )
    return QuotaSnapshotOut(tenant_id=tenant_id, tiers=out)


@router.put(
    "/tenants/{tenant_id}/tiers/{tier}",
    response_model=QuotaSpecOut,
)
async def update_quota_spec(
    tenant_id: str,
    tier: TierName,
    body: QuotaSpecUpdate,
    _user: User = Depends(require_permission(Permission.MANAGE_SUBSCRIPTIONS)),
) -> QuotaSpecOut:
    """更新某租户某 tier 的配额上限（None / 缺省 = 不限）。

    注：本期 spec 仅在内存里；进程重启回到默认。生产应把 PUT 也同步入库。
    """
    tracker = get_shared_tracker()
    new_spec = QuotaSpec(
        calls_per_day=body.calls_per_day,
        compute_ms_per_day=body.compute_ms_per_day,
        concurrent_executions=body.concurrent_executions,
    )
    # 直接写到 overrides；InMemoryQuotaTracker 暴露 _overrides 不公开，
    # 走构造时的 tenant_overrides 形态。
    tier_enum = SandboxTier(tier)
    overrides = tracker._overrides.setdefault(tenant_id, {})  # noqa: SLF001
    overrides[tier_enum] = new_spec

    return QuotaSpecOut(
        tier=tier,
        calls_per_day=new_spec.calls_per_day,
        compute_ms_per_day=new_spec.compute_ms_per_day,
        concurrent_executions=new_spec.concurrent_executions,
    )

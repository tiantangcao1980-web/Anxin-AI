# -*- coding: utf-8 -*-
"""
Skills 沙箱执行配额跟踪

设计动机（docs/v3/skills-sandbox-design.md §10 P4）：
    T4 远程沙箱（E2B / CodexCloud）按调用计费，必须**前置**限额：
        1. 单租户每日调用次数上限
        2. 单租户每日累计计算时长上限
        3. 单 skill 实例并发上限（防 burst 跑爆配额）

执行模型：
    - QuotaTracker 是协议；InMemoryQuotaTracker / RedisQuotaTracker 是实装
    - SkillSandboxRunner 在路由到 T2-T4 前调用 ``tracker.check_and_reserve(...)``
    - 执行结束后调 ``tracker.record_usage(...)`` 累加真实用量
    - check 失败 → PolicyGate-style DENY 结果，理由含 "quota_exceeded"

配额规则按租户分级（订阅 plan 决定上限），但本期仅暴露 ``QuotaSpec``，
具体 plan→quota 映射由 billing/Subscription 层注入。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from src.services.skill_sandbox.manifest import SandboxTier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuotaSpec:
    """租户对某 tier 的配额上限。

    上限缺省 ``None`` 表示不限。
    """

    calls_per_day: int | None = None
    compute_ms_per_day: int | None = None
    concurrent_executions: int | None = None


@dataclass(slots=True)
class QuotaUsage:
    """当前周期内的累计使用量。"""

    period_key: str       # YYYY-MM-DD（UTC）
    calls: int = 0
    compute_ms: int = 0
    in_flight: int = 0


@dataclass(slots=True)
class QuotaDecision:
    """check_and_reserve 的返回。"""

    allow: bool
    reason: str | None = None
    usage: QuotaUsage | None = None
    spec: QuotaSpec | None = None


# ---------------------------------------------------------------------------
# 协议
# ---------------------------------------------------------------------------


class QuotaTracker(Protocol):
    """配额追踪器协议。"""

    def get_spec(self, *, tenant_id: str, tier: SandboxTier) -> QuotaSpec: ...

    def check_and_reserve(
        self, *, tenant_id: str, tier: SandboxTier
    ) -> QuotaDecision: ...

    def record_usage(
        self,
        *,
        tenant_id: str,
        tier: SandboxTier,
        compute_ms: int,
        success: bool,
    ) -> None: ...

    def release_reservation(
        self, *, tenant_id: str, tier: SandboxTier
    ) -> None: ...


# ---------------------------------------------------------------------------
# 内存实现（测试 / 单进程默认）
# ---------------------------------------------------------------------------


def _utc_today_key(now: datetime | None = None) -> str:
    ref = now or datetime.now(UTC)
    return ref.date().isoformat()


class InMemoryQuotaTracker:
    """进程内实现 —— 重启即清零；用于测试与开发。

    Args:
        default_specs: ``{tier: QuotaSpec}``，可被 ``tenant_overrides`` 覆盖
        tenant_overrides: ``{tenant_id: {tier: QuotaSpec}}``
        now_provider: 注入当前时间，便于测试跨日重置
    """

    def __init__(
        self,
        *,
        default_specs: dict[SandboxTier, QuotaSpec] | None = None,
        tenant_overrides: dict[str, dict[SandboxTier, QuotaSpec]] | None = None,
        now_provider: Any = None,
    ) -> None:
        self._default_specs = dict(default_specs or {})
        self._overrides = {
            tid: dict(specs) for tid, specs in (tenant_overrides or {}).items()
        }
        self._now = now_provider or (lambda: datetime.now(UTC))
        # state[(tenant_id, tier)] -> QuotaUsage
        self._state: dict[tuple[str, str], QuotaUsage] = {}

    # ------------------------------------------------------------------
    # 公开
    # ------------------------------------------------------------------

    def get_spec(self, *, tenant_id: str, tier: SandboxTier) -> QuotaSpec:
        if tenant_id in self._overrides and tier in self._overrides[tenant_id]:
            return self._overrides[tenant_id][tier]
        return self._default_specs.get(tier, QuotaSpec())

    def check_and_reserve(
        self, *, tenant_id: str, tier: SandboxTier
    ) -> QuotaDecision:
        spec = self.get_spec(tenant_id=tenant_id, tier=tier)
        usage = self._touch_usage(tenant_id, tier)

        # 配额对 T0/T1 默认放行（不消耗）
        if tier in {SandboxTier.T0, SandboxTier.T1}:
            return QuotaDecision(allow=True, usage=usage, spec=spec)

        if spec.calls_per_day is not None and usage.calls >= spec.calls_per_day:
            return QuotaDecision(
                allow=False,
                reason=f"quota_exceeded:calls_per_day={spec.calls_per_day}",
                usage=usage,
                spec=spec,
            )
        if (
            spec.compute_ms_per_day is not None
            and usage.compute_ms >= spec.compute_ms_per_day
        ):
            return QuotaDecision(
                allow=False,
                reason=f"quota_exceeded:compute_ms_per_day={spec.compute_ms_per_day}",
                usage=usage,
                spec=spec,
            )
        if (
            spec.concurrent_executions is not None
            and usage.in_flight >= spec.concurrent_executions
        ):
            return QuotaDecision(
                allow=False,
                reason=f"quota_exceeded:concurrent={spec.concurrent_executions}",
                usage=usage,
                spec=spec,
            )

        # 占位计数（in_flight），release 或 record 时回收
        usage.in_flight += 1
        return QuotaDecision(allow=True, usage=usage, spec=spec)

    def record_usage(
        self,
        *,
        tenant_id: str,
        tier: SandboxTier,
        compute_ms: int,
        success: bool,
    ) -> None:
        if tier in {SandboxTier.T0, SandboxTier.T1}:
            return
        usage = self._touch_usage(tenant_id, tier)
        if usage.in_flight > 0:
            usage.in_flight -= 1
        # 计算时间无论成功失败都记账（避免恶意快速失败绕过）
        usage.compute_ms += max(0, int(compute_ms))
        # 但 calls 仅在 success 时计 —— 防 transient 网络抖动惩罚租户
        if success:
            usage.calls += 1

    def release_reservation(
        self, *, tenant_id: str, tier: SandboxTier
    ) -> None:
        if tier in {SandboxTier.T0, SandboxTier.T1}:
            return
        usage = self._touch_usage(tenant_id, tier)
        if usage.in_flight > 0:
            usage.in_flight -= 1

    # ------------------------------------------------------------------
    # 调试 / 内省
    # ------------------------------------------------------------------

    def snapshot(self, tenant_id: str, tier: SandboxTier) -> QuotaUsage:
        return self._touch_usage(tenant_id, tier)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _touch_usage(self, tenant_id: str, tier: SandboxTier) -> QuotaUsage:
        key = (tenant_id, tier.value)
        now = self._now()
        today = _utc_today_key(now)
        existing = self._state.get(key)
        if existing is None or existing.period_key != today:
            # 跨日重置：保留 in_flight（执行没结束）
            in_flight = existing.in_flight if existing else 0
            self._state[key] = QuotaUsage(period_key=today, in_flight=in_flight)
        return self._state[key]


# ---------------------------------------------------------------------------
# Redis 实现 —— 多进程共享，原子计数
# ---------------------------------------------------------------------------


class RedisQuotaTracker:
    """Redis 实装 —— 用 INCRBY + EXPIRE 实现按日重置。

    Keys（伪代码）::

        anxin:sbx:quota:{tenant}:{tier}:{YYYY-MM-DD}:calls          INT
        anxin:sbx:quota:{tenant}:{tier}:{YYYY-MM-DD}:compute_ms     INT
        anxin:sbx:quota:{tenant}:{tier}:in_flight                   INT

    Spec 解析与 InMemory 一致；只是计数走 Redis。
    Redis 不可用时 fail-closed：raise RedisUnavailable，
    SkillSandboxRunner 收到后按 DENIED 返回。
    """

    KEY_NS = "anxin:sbx:quota"
    TTL_SEC = 60 * 60 * 26  # 26h —— 跨日缓冲，避免临界点丢计数

    def __init__(
        self,
        *,
        redis_client: Any,                 # redis.asyncio.Redis 兼容客户端
        default_specs: dict[SandboxTier, QuotaSpec] | None = None,
        tenant_overrides: dict[str, dict[SandboxTier, QuotaSpec]] | None = None,
    ) -> None:
        if redis_client is None:
            raise ValueError("redis_client 不能为空")
        self.redis = redis_client
        self._default_specs = dict(default_specs or {})
        self._overrides = {
            tid: dict(specs) for tid, specs in (tenant_overrides or {}).items()
        }

    def get_spec(self, *, tenant_id: str, tier: SandboxTier) -> QuotaSpec:
        if tenant_id in self._overrides and tier in self._overrides[tenant_id]:
            return self._overrides[tenant_id][tier]
        return self._default_specs.get(tier, QuotaSpec())

    async def check_and_reserve(
        self, *, tenant_id: str, tier: SandboxTier
    ) -> QuotaDecision:
        spec = self.get_spec(tenant_id=tenant_id, tier=tier)
        if tier in {SandboxTier.T0, SandboxTier.T1}:
            return QuotaDecision(allow=True, spec=spec)

        today = _utc_today_key()
        calls_key = self._k(tenant_id, tier, today, "calls")
        compute_key = self._k(tenant_id, tier, today, "compute_ms")
        inflight_key = f"{self.KEY_NS}:{tenant_id}:{tier.value}:in_flight"

        # 先读取计数（不消费）
        calls, compute, in_flight = await self._mget_ints(
            calls_key, compute_key, inflight_key
        )

        if spec.calls_per_day is not None and calls >= spec.calls_per_day:
            return QuotaDecision(
                allow=False,
                reason=f"quota_exceeded:calls_per_day={spec.calls_per_day}",
                spec=spec,
            )
        if (
            spec.compute_ms_per_day is not None
            and compute >= spec.compute_ms_per_day
        ):
            return QuotaDecision(
                allow=False,
                reason=f"quota_exceeded:compute_ms_per_day={spec.compute_ms_per_day}",
                spec=spec,
            )
        if (
            spec.concurrent_executions is not None
            and in_flight >= spec.concurrent_executions
        ):
            return QuotaDecision(
                allow=False,
                reason=f"quota_exceeded:concurrent={spec.concurrent_executions}",
                spec=spec,
            )

        # 原子 +1 占位
        await self.redis.incr(inflight_key)
        return QuotaDecision(allow=True, spec=spec)

    async def record_usage(
        self,
        *,
        tenant_id: str,
        tier: SandboxTier,
        compute_ms: int,
        success: bool,
    ) -> None:
        if tier in {SandboxTier.T0, SandboxTier.T1}:
            return
        today = _utc_today_key()
        inflight_key = f"{self.KEY_NS}:{tenant_id}:{tier.value}:in_flight"
        try:
            await self.redis.decr(inflight_key)
            if success:
                ck = self._k(tenant_id, tier, today, "calls")
                await self.redis.incr(ck)
                await self.redis.expire(ck, self.TTL_SEC)
            if compute_ms > 0:
                cm = self._k(tenant_id, tier, today, "compute_ms")
                await self.redis.incrby(cm, int(compute_ms))
                await self.redis.expire(cm, self.TTL_SEC)
        except Exception:
            logger.exception("record_usage 写 Redis 失败 —— 计数可能短暂不一致")

    async def release_reservation(
        self, *, tenant_id: str, tier: SandboxTier
    ) -> None:
        if tier in {SandboxTier.T0, SandboxTier.T1}:
            return
        inflight_key = f"{self.KEY_NS}:{tenant_id}:{tier.value}:in_flight"
        try:
            await self.redis.decr(inflight_key)
        except Exception:
            logger.exception("release_reservation 写 Redis 失败")

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @classmethod
    def _k(cls, tenant_id: str, tier: SandboxTier, day: str, field: str) -> str:
        return f"{cls.KEY_NS}:{tenant_id}:{tier.value}:{day}:{field}"

    async def _mget_ints(self, *keys: str) -> tuple[int, ...]:
        vals = await self.redis.mget(*keys)
        out: list[int] = []
        for v in vals or []:
            if v is None:
                out.append(0)
                continue
            if isinstance(v, bytes):
                v = v.decode("ascii", errors="replace")
            try:
                out.append(int(v))
            except (TypeError, ValueError):
                out.append(0)
        return tuple(out)


__all__ = [
    "InMemoryQuotaTracker",
    "QuotaDecision",
    "QuotaSpec",
    "QuotaTracker",
    "QuotaUsage",
    "RedisQuotaTracker",
]

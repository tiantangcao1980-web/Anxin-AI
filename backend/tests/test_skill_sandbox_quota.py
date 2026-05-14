# -*- coding: utf-8 -*-
"""
配额跟踪单测

覆盖：
    - InMemoryQuotaTracker：
        * T0/T1 默认放行，不消费
        * calls 上限：N 次后 deny
        * compute_ms 上限：累计 ms 越线后 deny
        * concurrent：同时 in_flight 越线后 deny
        * record_usage(success=False) 不增加 calls，但增加 compute_ms
        * release_reservation 释放 in_flight
        * 跨日重置
    - 与 runner 集成：T2 skill 超额 → DENIED + reason 含 quota_exceeded
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

from src.core.deps import UserRole
from src.services.skill_registry import Skill
from src.services.skill_sandbox import (
    InMemoryQuotaTracker,
    QuotaSpec,
    SandboxManifest,
    SandboxTier,
    SkillSandboxRunner,
)
from src.services.skill_sandbox.runner import SkillSandboxStatus


# ---------------------------------------------------------------------------
# InMemoryQuotaTracker
# ---------------------------------------------------------------------------


def test_t0_t1_never_denied_by_quota() -> None:
    t = InMemoryQuotaTracker(
        default_specs={SandboxTier.T2: QuotaSpec(calls_per_day=0)}
    )
    for tier in (SandboxTier.T0, SandboxTier.T1):
        d = t.check_and_reserve(tenant_id="org-x", tier=tier)
        assert d.allow, f"{tier} 不应受配额限制"


def test_calls_per_day_enforced() -> None:
    t = InMemoryQuotaTracker(
        default_specs={SandboxTier.T2: QuotaSpec(calls_per_day=2)}
    )
    for i in range(2):
        d = t.check_and_reserve(tenant_id="org-x", tier=SandboxTier.T2)
        assert d.allow
        t.record_usage(tenant_id="org-x", tier=SandboxTier.T2, compute_ms=10, success=True)
    d = t.check_and_reserve(tenant_id="org-x", tier=SandboxTier.T2)
    assert not d.allow
    assert "calls_per_day=2" in (d.reason or "")


def test_compute_ms_per_day_enforced() -> None:
    t = InMemoryQuotaTracker(
        default_specs={SandboxTier.T2: QuotaSpec(compute_ms_per_day=100)}
    )
    d = t.check_and_reserve(tenant_id="org-x", tier=SandboxTier.T2)
    assert d.allow
    t.record_usage(tenant_id="org-x", tier=SandboxTier.T2, compute_ms=120, success=True)
    d = t.check_and_reserve(tenant_id="org-x", tier=SandboxTier.T2)
    assert not d.allow
    assert "compute_ms_per_day=100" in (d.reason or "")


def test_concurrent_enforced() -> None:
    t = InMemoryQuotaTracker(
        default_specs={SandboxTier.T2: QuotaSpec(concurrent_executions=1)}
    )
    d1 = t.check_and_reserve(tenant_id="org-x", tier=SandboxTier.T2)
    assert d1.allow
    d2 = t.check_and_reserve(tenant_id="org-x", tier=SandboxTier.T2)
    assert not d2.allow
    assert "concurrent=1" in (d2.reason or "")
    # 释放一个名额
    t.release_reservation(tenant_id="org-x", tier=SandboxTier.T2)
    d3 = t.check_and_reserve(tenant_id="org-x", tier=SandboxTier.T2)
    assert d3.allow


def test_failed_call_does_not_increment_calls_but_does_compute_ms() -> None:
    t = InMemoryQuotaTracker(
        default_specs={
            SandboxTier.T2: QuotaSpec(calls_per_day=2, compute_ms_per_day=100)
        }
    )
    t.check_and_reserve(tenant_id="org-x", tier=SandboxTier.T2)
    t.record_usage(tenant_id="org-x", tier=SandboxTier.T2, compute_ms=50, success=False)
    snap = t.snapshot("org-x", SandboxTier.T2)
    assert snap.calls == 0
    assert snap.compute_ms == 50
    assert snap.in_flight == 0


def test_tenant_override_takes_precedence() -> None:
    t = InMemoryQuotaTracker(
        default_specs={SandboxTier.T2: QuotaSpec(calls_per_day=1)},
        tenant_overrides={"vip-org": {SandboxTier.T2: QuotaSpec(calls_per_day=999)}},
    )
    d = t.check_and_reserve(tenant_id="vip-org", tier=SandboxTier.T2)
    assert d.allow
    spec = t.get_spec(tenant_id="vip-org", tier=SandboxTier.T2)
    assert spec.calls_per_day == 999


def test_period_resets_on_new_utc_day() -> None:
    fake_now = [datetime(2026, 5, 14, 23, 50, tzinfo=timezone.utc)]
    t = InMemoryQuotaTracker(
        default_specs={SandboxTier.T2: QuotaSpec(calls_per_day=1)},
        now_provider=lambda: fake_now[0],
    )
    t.check_and_reserve(tenant_id="o", tier=SandboxTier.T2)
    t.record_usage(tenant_id="o", tier=SandboxTier.T2, compute_ms=10, success=True)
    # 同一天
    d = t.check_and_reserve(tenant_id="o", tier=SandboxTier.T2)
    assert not d.allow
    # 跨日
    fake_now[0] = datetime(2026, 5, 15, 0, 5, tzinfo=timezone.utc)
    d2 = t.check_and_reserve(tenant_id="o", tier=SandboxTier.T2)
    assert d2.allow


# ---------------------------------------------------------------------------
# Runner 集成
# ---------------------------------------------------------------------------


def _register_tmp(name: str, fn) -> None:
    mod = types.ModuleType(name)
    mod.run = fn
    sys.modules[name] = mod


@pytest.mark.asyncio
async def test_runner_denies_on_quota_exceeded() -> None:
    """T1 skill 受限于 calls_per_day=0 时，runner 应直接 DENIED + 含 quota 原因。"""
    _register_tmp("anxin_quota_skill", lambda payload: payload)

    # 注意：T1 实际 tracker 内部不会限额（T0/T1 默认放行）；
    # 这里改成 T2 才能看到限流；T2 需要 LocalProvider 拉起子进程。
    # 用 mock provider 避免真起进程：提供一个 inline T2 runner overrides。
    from src.services.sandbox_executor import (
        BaseSandboxProvider,
        Sandbox,
        SandboxProviderRegistry,
        SandboxSpec,
        SandboxStatus,
        ExecResult,
    )

    class _FakeProvider(BaseSandboxProvider):
        provider_type = "fake"

        async def provision(self, spec: SandboxSpec):
            return Sandbox(provider_type="fake", status=SandboxStatus.RUNNING, spec=spec, metadata={})

        async def terminate(self, sandbox):
            sandbox.status = SandboxStatus.TERMINATED

        async def exec(self, sandbox, cmd, stdin=None, timeout_sec=None):
            return ExecResult(stdout="ok", stderr="", exit_code=0, duration_ms=1, cmd=list(cmd))

        async def upload(self, sandbox, src_path, dst_path):
            pass

        async def download(self, sandbox, sandbox_path):
            return b""

        def stream_logs(self, sandbox):  # pragma: no cover
            raise NotImplementedError

    SandboxProviderRegistry._registry["fake"] = _FakeProvider

    tracker = InMemoryQuotaTracker(
        default_specs={SandboxTier.T2: QuotaSpec(calls_per_day=0)}
    )
    runner = SkillSandboxRunner(
        quota_tracker=tracker,
        provider_overrides={SandboxTier.T2: "fake"},
    )
    manifest = SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T2",
            "entrypoint": "x:y",
        }
    })
    result = await runner.execute(
        skill=Skill(name="x", description="x"),
        manifest=manifest,
        payload={},
        user_id="u1",
        user_role=UserRole.LAWYER.value,
        tenant_id="t1",
    )
    assert result.status == SkillSandboxStatus.DENIED
    assert "quota_exceeded" in (result.error or "")


@pytest.mark.asyncio
async def test_runner_records_usage_on_success() -> None:
    """T1 成功执行应不影响配额（T1/T0 跳过 tracker 计数）。"""
    _register_tmp("anxin_quota_skill2", lambda payload: 42)
    tracker = InMemoryQuotaTracker()
    runner = SkillSandboxRunner(quota_tracker=tracker)
    manifest = SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T1",
            "entrypoint": "anxin_quota_skill2:run",
            "signature": {"algo": "ed25519", "publisher": "anxin-platform", "sig": "AAAA"},
        }
    })
    res = await runner.execute(
        skill=Skill(name="ok", description="ok"),
        manifest=manifest,
        payload={},
        user_id="u",
        user_role=UserRole.LAWYER.value,
        tenant_id="t",
    )
    assert res.status == SkillSandboxStatus.SUCCESS
    snap = tracker.snapshot("t", SandboxTier.T1)
    assert snap.calls == 0  # T1 不计数

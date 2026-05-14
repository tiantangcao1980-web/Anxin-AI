# -*- coding: utf-8 -*-
"""
SkillSandboxRunner 单测

覆盖：
    - T0 → handled=False（runner 不接管）
    - T1 in-process 成功（同步函数）
    - T1 in-process 成功（async 函数）
    - T1 超时
    - T1 entrypoint 找不到函数 → FAILED
    - 权限闸门拒绝 → DENIED
    - audit_hook 被调用且 payload 含关键字段
"""

from __future__ import annotations

import asyncio
import sys
import types

import pytest

from src.core.deps import Permission, UserRole
from src.services.skill_registry import Skill
from src.services.skill_sandbox import (
    PolicyGate,
    SandboxManifest,
    SandboxTier,
    SkillSandboxResult,
    SkillSandboxRunner,
)
from src.services.skill_sandbox.runner import SkillSandboxStatus


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _register_tmp_module(name: str, namespace: dict) -> None:
    """临时挂一个模块到 sys.modules，便于 entrypoint 找得到。"""
    mod = types.ModuleType(name)
    for k, v in namespace.items():
        setattr(mod, k, v)
    sys.modules[name] = mod


def _skill(name: str = "tmp_skill") -> Skill:
    return Skill(name=name, description="test skill")


def _signed_t1(entrypoint: str) -> SandboxManifest:
    return SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T1",
            "entrypoint": entrypoint,
            "signature": {
                "algo": "ed25519",
                "publisher": "anxin-platform",
                "sig": "AAAA",
            },
        }
    })


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t0_not_handled() -> None:
    runner = SkillSandboxRunner()
    manifest = SandboxManifest.from_frontmatter(None)
    result = await runner.execute(
        skill=_skill(),
        manifest=manifest,
        payload={},
        user_id="u1",
        user_role=UserRole.LAWYER.value,
    )
    assert result.handled is False
    assert result.status == SkillSandboxStatus.NOT_HANDLED


@pytest.mark.asyncio
async def test_t1_in_process_sync_ok() -> None:
    def run(payload):
        return {"echo": payload}
    _register_tmp_module("anxin_test_skill_sync", {"run": run})

    runner = SkillSandboxRunner()
    manifest = _signed_t1("anxin_test_skill_sync:run")
    result = await runner.execute(
        skill=_skill(),
        manifest=manifest,
        payload={"a": 1},
        user_id="u1",
        user_role=UserRole.LAWYER.value,
    )
    assert result.status == SkillSandboxStatus.SUCCESS, result.error
    assert result.output == {"echo": {"a": 1}}
    assert result.manifest_fingerprint is not None


@pytest.mark.asyncio
async def test_t1_in_process_async_ok() -> None:
    async def run(payload):
        await asyncio.sleep(0)
        return payload["x"] * 2
    _register_tmp_module("anxin_test_skill_async", {"run": run})

    runner = SkillSandboxRunner()
    manifest = _signed_t1("anxin_test_skill_async:run")
    result = await runner.execute(
        skill=_skill(),
        manifest=manifest,
        payload={"x": 21},
        user_id="u1",
        user_role=UserRole.LAWYER.value,
    )
    assert result.status == SkillSandboxStatus.SUCCESS
    assert result.output == 42


@pytest.mark.asyncio
async def test_t1_timeout_enforced() -> None:
    async def run(_payload):
        await asyncio.sleep(5)
        return "never"
    _register_tmp_module("anxin_test_skill_timeout", {"run": run})

    runner = SkillSandboxRunner()
    manifest = SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T1",
            "entrypoint": "anxin_test_skill_timeout:run",
            "resource_limits": {"timeout_sec": 1},
            "signature": {"algo": "ed25519", "publisher": "anxin-platform", "sig": "x"},
        }
    })
    result = await runner.execute(
        skill=_skill(),
        manifest=manifest,
        payload={},
        user_id="u1",
        user_role=UserRole.LAWYER.value,
    )
    assert result.status == SkillSandboxStatus.TIMEOUT


@pytest.mark.asyncio
async def test_t1_entrypoint_function_missing() -> None:
    _register_tmp_module("anxin_test_skill_missing", {})  # 空模块
    runner = SkillSandboxRunner()
    manifest = _signed_t1("anxin_test_skill_missing:run")
    result = await runner.execute(
        skill=_skill(),
        manifest=manifest,
        payload={},
        user_id="u1",
        user_role=UserRole.LAWYER.value,
    )
    assert result.status == SkillSandboxStatus.FAILED


@pytest.mark.asyncio
async def test_permission_gate_denies() -> None:
    """skill 要求 write:documents，但 individual_user 没有该权限。"""
    def run(_payload):
        return "should not run"
    _register_tmp_module("anxin_test_skill_denied", {"run": run})

    runner = SkillSandboxRunner(policy_gate=PolicyGate(environment="production"))
    manifest = SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T1",
            "entrypoint": "anxin_test_skill_denied:run",
            "permissions": [Permission.WRITE_DOCUMENTS.value],
            "signature": {"algo": "ed25519", "publisher": "anxin-platform", "sig": "x"},
        }
    })
    result = await runner.execute(
        skill=_skill(),
        manifest=manifest,
        payload={},
        user_id="u1",
        user_role=UserRole.INDIVIDUAL_USER.value,
    )
    assert result.status == SkillSandboxStatus.DENIED
    assert result.error and "缺少权限" in result.error


@pytest.mark.asyncio
async def test_audit_hook_invoked_on_success() -> None:
    def run(payload):
        return payload
    _register_tmp_module("anxin_test_skill_audit", {"run": run})

    captured: list[dict] = []

    runner = SkillSandboxRunner(audit_hook=lambda payload: captured.append(payload))
    manifest = _signed_t1("anxin_test_skill_audit:run")
    await runner.execute(
        skill=_skill("audit-skill"),
        manifest=manifest,
        payload={"k": "v"},
        user_id="u1",
        user_role=UserRole.LAWYER.value,
        tenant_id="org-1",
        trace_id="trace-x",
    )
    assert len(captured) == 1
    payload = captured[0]
    assert payload["skill_name"] == "audit-skill"
    assert payload["tier"] == "T1"
    assert payload["status"] == "success"
    assert payload["user_id"] == "u1"
    assert payload["tenant_id"] == "org-1"
    assert payload["trace_id"] == "trace-x"
    assert payload["manifest_fingerprint"]


@pytest.mark.asyncio
async def test_audit_hook_invoked_on_denied() -> None:
    captured: list[dict] = []
    runner = SkillSandboxRunner(audit_hook=lambda p: captured.append(p))
    manifest = SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T1",
            "entrypoint": "x:y",
            "permissions": [Permission.WRITE_DOCUMENTS.value],
            "signature": {"algo": "ed25519", "publisher": "anxin-platform", "sig": "x"},
        }
    })
    await runner.execute(
        skill=_skill(),
        manifest=manifest,
        payload={},
        user_id="u1",
        user_role=UserRole.INDIVIDUAL_USER.value,
    )
    assert len(captured) == 1
    assert captured[0]["status"] == "denied"
    assert captured[0]["denied_reason"]

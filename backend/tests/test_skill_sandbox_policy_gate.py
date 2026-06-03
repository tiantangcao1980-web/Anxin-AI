# -*- coding: utf-8 -*-
"""
PolicyGate 单测

覆盖：
    - manifest 不要求权限 → 允许
    - manifest 要求 read:documents，user 是 individual_user（没有）→ 拒绝并列出 missing
    - manifest 要求 read:documents，user 是 lawyer（有）→ 允许
    - manifest.permissions 含未知权限名 → 拒绝
    - tier=T1 无签名 → 拒绝
    - network.mode=full 在 production 环境 → 拒绝
    - network.mode=full 在 development 环境 → 允许
"""

from __future__ import annotations

from src.core.deps import Permission, UserRole
from src.services.skill_sandbox import (
    PolicyDecision,
    PolicyGate,
    SandboxManifest,
    SandboxTier,
)


def _manifest(**sandbox_overrides) -> SandboxManifest:
    base = {"tier": "T2", "entrypoint": "m:f"}
    base.update(sandbox_overrides)
    return SandboxManifest.from_frontmatter({"sandbox": base})


def test_allow_when_no_permissions_required() -> None:
    gate = PolicyGate(environment="production")
    res = gate.check(
        manifest=_manifest(),
        user_role=UserRole.INDIVIDUAL_USER.value,
    )
    assert res.allow


def test_deny_when_missing_permission() -> None:
    gate = PolicyGate(environment="production")
    res = gate.check(
        manifest=_manifest(permissions=[Permission.WRITE_DOCUMENTS.value]),
        user_role=UserRole.INDIVIDUAL_USER.value,
    )
    assert not res.allow
    assert res.decision == PolicyDecision.DENY
    assert res.missing_permissions == [Permission.WRITE_DOCUMENTS.value]


def test_allow_when_role_has_permission() -> None:
    gate = PolicyGate(environment="production")
    res = gate.check(
        manifest=_manifest(permissions=[Permission.READ_DOCUMENTS.value]),
        user_role=UserRole.LAWYER.value,
    )
    assert res.allow


def test_unknown_permission_rejected() -> None:
    gate = PolicyGate(environment="production")
    res = gate.check(
        manifest=_manifest(permissions=["read:nonexistent"]),
        user_role=UserRole.LAWYER.value,
    )
    assert not res.allow
    assert "未知权限" in (res.reason or "")


def test_t1_unsigned_denied() -> None:
    gate = PolicyGate(environment="production", allow_unsigned_t1=False)
    # 直接构造一个对象，绕过 manifest 校验路径（因为正常构造会拒绝无签名 T1）
    # 这里用 model_construct 跳过 validator
    m = SandboxManifest.model_construct(
        tier=SandboxTier.T1,
        entrypoint="m:f",
        signature=None,
    )
    res = gate.check(manifest=m, user_role=UserRole.LAWYER.value)
    assert not res.allow
    assert "T1" in (res.reason or "")


def test_full_network_denied_in_production() -> None:
    gate = PolicyGate(environment="production")
    res = gate.check(
        manifest=_manifest(network={"mode": "full"}),
        user_role=UserRole.LAWYER.value,
    )
    assert not res.allow
    assert "full" in (res.reason or "")


def test_full_network_allowed_in_dev() -> None:
    gate = PolicyGate(environment="development")
    res = gate.check(
        manifest=_manifest(network={"mode": "full"}),
        user_role=UserRole.LAWYER.value,
    )
    assert res.allow

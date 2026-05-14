# -*- coding: utf-8 -*-
"""
SandboxManifest 解析 / 校验单测

覆盖：
    - 默认 T0
    - tier=T2 + entrypoint 通过
    - tier=T1 缺签名 → 拒绝
    - code tier 缺 entrypoint → 拒绝
    - T0 误带 entrypoint → 拒绝
    - 路径越界 ..  → 拒绝
    - mode=allowlist 必须给 allowed_hosts
    - fingerprint 稳定
"""

from __future__ import annotations

import pytest

from src.services.skill_sandbox import (
    ManifestValidationError,
    SandboxManifest,
    SandboxTier,
)


def test_empty_frontmatter_defaults_to_t0() -> None:
    m = SandboxManifest.from_frontmatter(None)
    assert m.tier == SandboxTier.T0
    assert m.entrypoint is None
    assert m.fingerprint().startswith("sha256:")


def test_no_sandbox_block_defaults_to_t0() -> None:
    m = SandboxManifest.from_frontmatter({"name": "x"})
    assert m.tier == SandboxTier.T0


def test_t2_with_entrypoint_ok() -> None:
    m = SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T2",
            "entrypoint": "pkg.module:run",
            "runtime": "python3.11",
            "permissions": ["read:documents"],
        }
    })
    assert m.tier == SandboxTier.T2
    assert m.entrypoint == "pkg.module:run"


def test_code_tier_missing_entrypoint_rejected() -> None:
    with pytest.raises(ManifestValidationError):
        SandboxManifest.from_frontmatter({
            "sandbox": {"tier": "T2"}
        })


def test_t0_with_entrypoint_rejected() -> None:
    with pytest.raises(ManifestValidationError):
        SandboxManifest.from_frontmatter({
            "sandbox": {"tier": "T0", "entrypoint": "m:f"}
        })


def test_t1_requires_signature() -> None:
    with pytest.raises(ManifestValidationError):
        SandboxManifest.from_frontmatter({
            "sandbox": {
                "tier": "T1",
                "entrypoint": "m:f",
            }
        })


def test_t1_with_signature_ok() -> None:
    m = SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T1",
            "entrypoint": "m:f",
            "signature": {
                "algo": "ed25519",
                "publisher": "anxin-platform",
                "sig": "AAAA",
            },
        }
    })
    assert m.signature is not None
    assert m.signature.publisher == "anxin-platform"


def test_entrypoint_must_be_module_colon_func() -> None:
    with pytest.raises(ManifestValidationError):
        SandboxManifest.from_frontmatter({
            "sandbox": {"tier": "T2", "entrypoint": "no_colon"}
        })


def test_filesystem_rejects_relative_path() -> None:
    with pytest.raises(ManifestValidationError):
        SandboxManifest.from_frontmatter({
            "sandbox": {
                "tier": "T2",
                "entrypoint": "m:f",
                "filesystem": {"read": ["../etc/passwd"]},
            }
        })


def test_filesystem_rejects_non_absolute() -> None:
    with pytest.raises(ManifestValidationError):
        SandboxManifest.from_frontmatter({
            "sandbox": {
                "tier": "T2",
                "entrypoint": "m:f",
                "filesystem": {"read": ["relative/path"]},
            }
        })


def test_network_allowlist_requires_hosts() -> None:
    with pytest.raises(ManifestValidationError):
        SandboxManifest.from_frontmatter({
            "sandbox": {
                "tier": "T2",
                "entrypoint": "m:f",
                "network": {"mode": "allowlist"},
            }
        })


def test_network_none_rejects_hosts() -> None:
    with pytest.raises(ManifestValidationError):
        SandboxManifest.from_frontmatter({
            "sandbox": {
                "tier": "T2",
                "entrypoint": "m:f",
                "network": {"mode": "none", "allowed_hosts": ["example.com"]},
            }
        })


def test_missing_tier_with_entrypoint_defaults_to_t3() -> None:
    """设计文档 §3.1：缺 tier 但有 entrypoint → 隐含 T3（最严）。"""
    m = SandboxManifest.from_frontmatter({
        "sandbox": {"entrypoint": "m:f"}
    })
    assert m.tier == SandboxTier.T3


def test_fingerprint_stable() -> None:
    fm1 = {
        "sandbox": {
            "tier": "T2",
            "entrypoint": "m:f",
            "permissions": ["read:documents"],
        }
    }
    fm2 = {
        "sandbox": {
            "entrypoint": "m:f",
            "permissions": ["read:documents"],
            "tier": "T2",
        }
    }
    a = SandboxManifest.from_frontmatter(fm1).fingerprint()
    b = SandboxManifest.from_frontmatter(fm2).fingerprint()
    assert a == b


def test_fingerprint_changes_with_content() -> None:
    a = SandboxManifest.from_frontmatter({
        "sandbox": {"tier": "T2", "entrypoint": "m:f", "permissions": ["read:documents"]}
    }).fingerprint()
    b = SandboxManifest.from_frontmatter({
        "sandbox": {"tier": "T2", "entrypoint": "m:f", "permissions": ["write:documents"]}
    }).fingerprint()
    assert a != b


def test_isolation_level_monotonic() -> None:
    levels = [SandboxTier.T0, SandboxTier.T1, SandboxTier.T2, SandboxTier.T3, SandboxTier.T4]
    values = [t.isolation_level for t in levels]
    assert values == sorted(values)

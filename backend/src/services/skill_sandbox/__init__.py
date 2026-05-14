# -*- coding: utf-8 -*-
"""
skill_sandbox —— SKILL.md 到 sandbox_executor 的桥接层

设计见 docs/v3/skills-sandbox-design.md。

公开 API:
    - SandboxManifest      : 从 SKILL.md frontmatter 解析的沙箱声明
    - SandboxTier          : T0 / T1 / T2 / T3 / T4
    - SkillSandboxRunner   : 信任分级路由 + 权限闸门 + 审计
    - ManifestValidationError
"""

from src.services.skill_sandbox.manifest import (
    ManifestValidationError,
    SandboxManifest,
    SandboxTier,
)
from src.services.skill_sandbox.policy_gate import (
    PolicyDecision,
    PolicyGate,
    PolicyGateResult,
)
from src.services.skill_sandbox.quota import (
    InMemoryQuotaTracker,
    QuotaDecision,
    QuotaSpec,
    QuotaTracker,
    QuotaUsage,
    RedisQuotaTracker,
)
from src.services.skill_sandbox.runner import (
    SkillSandboxResult,
    SkillSandboxRunner,
)
from src.services.skill_sandbox.signature import (
    SignatureVerifier,
    load_publisher_keys_from_env,
    load_publisher_keys_from_settings,
)

__all__ = [
    "InMemoryQuotaTracker",
    "ManifestValidationError",
    "PolicyDecision",
    "PolicyGate",
    "PolicyGateResult",
    "QuotaDecision",
    "QuotaSpec",
    "QuotaTracker",
    "QuotaUsage",
    "RedisQuotaTracker",
    "SandboxManifest",
    "SandboxTier",
    "SignatureVerifier",
    "SkillSandboxResult",
    "SkillSandboxRunner",
    "load_publisher_keys_from_env",
    "load_publisher_keys_from_settings",
]

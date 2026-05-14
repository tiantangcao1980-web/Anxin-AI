# -*- coding: utf-8 -*-
"""
PolicyGate —— Skills 沙箱执行的权限闸门

设计见 docs/v3/skills-sandbox-design.md §5。

职责：
    1. 把 SandboxManifest.permissions 映射成 core.deps.Permission 枚举
    2. 校验调用者是否拥有这些权限（**复用现有 ROLE_PERMISSIONS**）
    3. 把 tier 映射成一个粗粒度风险级别，用于和环境策略对照
    4. 返回结构化决策（allow / deny + 原因），交给 runner 决定如何对外

为何独立成模块：runner 无需关心权限细节，只看 PolicyGateResult.allow；
未来要接 CapabilityPolicyEngine 时只改这一处。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.deps import Permission, get_user_permissions
from src.services.skill_sandbox.manifest import SandboxManifest, SandboxTier
from src.services.skill_sandbox.signature import SignatureVerifier


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(slots=True)
class PolicyGateResult:
    """权限闸门决策。"""

    decision: PolicyDecision
    reason: str | None = None
    missing_permissions: list[str] | None = None

    @property
    def allow(self) -> bool:
        return self.decision == PolicyDecision.ALLOW


# tier → 风险级别，对应 docs/openspec §3.7-3.8 的 L0-L5
_TIER_RISK_LEVEL: dict[SandboxTier, int] = {
    SandboxTier.T0: 0,   # 纯 prompt
    SandboxTier.T1: 1,   # in-process trusted
    SandboxTier.T2: 2,   # subprocess
    SandboxTier.T3: 3,   # container
    SandboxTier.T4: 4,   # remote
}


class PolicyGate:
    """权限闸门 —— fail-closed。"""

    def __init__(
        self,
        *,
        environment: str = "production",
        allow_unsigned_t1: bool = False,
        signature_verifier: SignatureVerifier | None = None,
    ) -> None:
        self.environment = (environment or "production").lower()
        self.allow_unsigned_t1 = allow_unsigned_t1
        self.signature_verifier = signature_verifier

    # ------------------------------------------------------------------
    # 决策入口
    # ------------------------------------------------------------------

    def check(
        self,
        *,
        manifest: SandboxManifest,
        user_role: str,
        user_permissions: set[Permission] | None = None,
    ) -> PolicyGateResult:
        """对一次沙箱执行做权限决策。

        Args:
            manifest: SkillSandbox manifest
            user_role: 调用者角色（``user.role``）
            user_permissions: 可选预算好的权限集；缺省走 ``get_user_permissions(user_role)``。
        """
        # 1) tier 与环境一致性
        env_check = self._check_env_tier(manifest)
        if not env_check.allow:
            return env_check

        # 2) T1 签名硬要求 + 真签名校验
        if manifest.tier == SandboxTier.T1:
            if manifest.signature is None:
                if not self.allow_unsigned_t1:
                    return PolicyGateResult(
                        decision=PolicyDecision.DENY,
                        reason="T1 skill 未签名（in-process 受信级别）",
                    )
            elif self.signature_verifier is not None:
                # 接入真校验：缺公钥 / 解码错 / 签名假 都被 verify 转成 False
                if not self.signature_verifier.verify(manifest):
                    return PolicyGateResult(
                        decision=PolicyDecision.DENY,
                        reason=f"T1 签名校验失败 publisher={manifest.signature.publisher}",
                    )

        # 3) 网络策略 vs 环境
        if manifest.network.mode.value == "full" and self.environment not in {"development", "test"}:
            return PolicyGateResult(
                decision=PolicyDecision.DENY,
                reason="network.mode=full 仅在 development/test 允许",
            )

        # 4) 权限交集：调用者必须包含 manifest.permissions 中**全部**枚举
        if manifest.permissions:
            resolved = user_permissions if user_permissions is not None else get_user_permissions(user_role)
            missing: list[str] = []
            for raw in manifest.permissions:
                try:
                    perm = Permission(raw)
                except ValueError:
                    return PolicyGateResult(
                        decision=PolicyDecision.DENY,
                        reason=f"manifest.permissions 含未知权限: {raw!r}",
                    )
                if perm not in resolved:
                    missing.append(perm.value)
            if missing:
                return PolicyGateResult(
                    decision=PolicyDecision.DENY,
                    reason=f"缺少权限: {', '.join(missing)}",
                    missing_permissions=missing,
                )

        return PolicyGateResult(decision=PolicyDecision.ALLOW)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _check_env_tier(self, manifest: SandboxManifest) -> PolicyGateResult:
        """生产环境禁止某些松散 tier 组合。"""
        # 目前没有"按 env 禁某 tier"的硬规则；保留扩展点
        return PolicyGateResult(decision=PolicyDecision.ALLOW)

    @staticmethod
    def risk_level(manifest: SandboxManifest) -> int:
        """暴露给 audit / governance 的粗粒度风险等级。"""
        return _TIER_RISK_LEVEL.get(manifest.tier, 5)

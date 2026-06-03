# -*- coding: utf-8 -*-
"""
SkillSandboxRunner —— Skills 沙箱执行核心

设计见 docs/v3/skills-sandbox-design.md §4。

调用者:
    1. 从 SkillRegistry 拿到 Skill
    2. 用 ``SandboxManifest.from_frontmatter(...)`` 解析 manifest
    3. 调 ``runner.execute(skill, manifest, payload, user_role=..., user_id=...)``
    4. 拿到 SkillSandboxResult（success / denied / failed / timeout）

如果 manifest.tier == T0（默认），runner **不接管**执行，调用者应回退到
``SkillExecutor`` 走 prompt 通路；这是显式的 ``SkillSandboxResult(handled=False)``，
便于调用方写线性代码而无需在两条路径之间分支。
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.services.sandbox_executor import (
    NetworkPolicy,
    NetworkPolicyMode,
    ResourceLimits,
    SandboxProviderRegistry,
    SandboxSpec,
)
from src.services.skill_registry import Skill
from src.services.skill_sandbox.manifest import (
    NetworkMode,
    SandboxManifest,
    SandboxTier,
)
from src.services.skill_sandbox.policy_gate import (
    PolicyGate,
    PolicyGateResult,
)
from src.services.skill_sandbox.quota import (
    InMemoryQuotaTracker,
    QuotaTracker,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 结果模型
# ---------------------------------------------------------------------------


class SkillSandboxStatus(str, Enum):
    """沙箱执行最终状态。"""

    NOT_HANDLED = "not_handled"   # T0：runner 不接管，调用方走 prompt 路径
    SUCCESS = "success"
    DENIED = "denied"             # 权限闸门拒绝
    TIMEOUT = "timeout"
    FAILED = "failed"


@dataclass(slots=True)
class SkillSandboxResult:
    """沙箱执行结果（统一所有 tier 的返回值）。"""

    skill_name: str
    status: SkillSandboxStatus
    tier: SandboxTier
    output: Any = None
    error: str | None = None
    duration_ms: int = 0
    manifest_fingerprint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def handled(self) -> bool:
        return self.status != SkillSandboxStatus.NOT_HANDLED

    @property
    def succeeded(self) -> bool:
        return self.status == SkillSandboxStatus.SUCCESS


# ---------------------------------------------------------------------------
# 审计回调
# ---------------------------------------------------------------------------


AuditCallback = "callable[[dict[str, Any]], None] | None"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class SkillSandboxRunner:
    """SKILL.md → sandbox_executor 的桥接 runner。

    参数:
        policy_gate: 权限闸门；默认按 ``settings.ENVIRONMENT`` 实例化。
        audit_hook:  可选 callable，每次执行后被调用，参数是审计 payload dict。
        provider_overrides: tier → provider_type 的映射覆盖，便于测试。
    """

    DEFAULT_TIER_TO_PROVIDER: dict[SandboxTier, str] = {
        SandboxTier.T2: "local",
        SandboxTier.T3: "docker",
        SandboxTier.T4: "e2b",
    }

    def __init__(
        self,
        *,
        policy_gate: PolicyGate | None = None,
        audit_hook: Any = None,
        provider_overrides: dict[SandboxTier, str] | None = None,
        quota_tracker: QuotaTracker | None = None,
    ) -> None:
        if policy_gate is None:
            try:
                from src.core.config import settings
                env = getattr(settings, "ENVIRONMENT", "production")
            except Exception:
                env = "production"
            policy_gate = PolicyGate(environment=env)
        self.policy_gate = policy_gate
        self.audit_hook = audit_hook
        self._tier_to_provider = {
            **self.DEFAULT_TIER_TO_PROVIDER,
            **(provider_overrides or {}),
        }
        # 缺省内存配额（无上限），生产应注入 RedisQuotaTracker
        self.quota_tracker: QuotaTracker = quota_tracker or InMemoryQuotaTracker()

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def execute(
        self,
        *,
        skill: Skill,
        manifest: SandboxManifest,
        payload: dict[str, Any] | None = None,
        user_id: str,
        user_role: str,
        tenant_id: str | None = None,
        trace_id: str | None = None,
    ) -> SkillSandboxResult:
        """按 tier 路由并执行一次 skill。

        T0 → 不接管。
        T1 → in-process import 调用。
        T2-T4 → 走 SandboxProviderRegistry。

        无论哪条路径，最终都会调用 ``audit_hook``（如果配置了）。
        """
        started = time.monotonic()
        fingerprint = manifest.fingerprint()

        # T0：不接管
        if not manifest.tier.is_code:
            return SkillSandboxResult(
                skill_name=skill.name,
                status=SkillSandboxStatus.NOT_HANDLED,
                tier=manifest.tier,
                manifest_fingerprint=fingerprint,
            )

        # 权限闸门
        gate = self.policy_gate.check(manifest=manifest, user_role=user_role)
        if not gate.allow:
            result = SkillSandboxResult(
                skill_name=skill.name,
                status=SkillSandboxStatus.DENIED,
                tier=manifest.tier,
                error=gate.reason,
                manifest_fingerprint=fingerprint,
                duration_ms=int((time.monotonic() - started) * 1000),
                metadata={"missing_permissions": gate.missing_permissions or []},
            )
            self._audit(result, user_id=user_id, tenant_id=tenant_id, trace_id=trace_id, gate=gate)
            return result

        # 配额闸门（T0/T1 在 tracker 内部直接放行）
        quota_decision = await _maybe_await_quota(
            self.quota_tracker.check_and_reserve(
                tenant_id=tenant_id or "_anonymous_",
                tier=manifest.tier,
            )
        )
        if not quota_decision.allow:
            result = SkillSandboxResult(
                skill_name=skill.name,
                status=SkillSandboxStatus.DENIED,
                tier=manifest.tier,
                error=quota_decision.reason or "quota_exceeded",
                manifest_fingerprint=fingerprint,
                duration_ms=int((time.monotonic() - started) * 1000),
                metadata={"quota_reason": quota_decision.reason},
            )
            self._audit(result, user_id=user_id, tenant_id=tenant_id, trace_id=trace_id, gate=gate)
            return result

        # 路由
        try:
            if manifest.tier == SandboxTier.T1:
                result = await self._run_in_process(skill, manifest, payload or {})
            else:
                result = await self._run_via_provider(skill, manifest, payload or {})
        except TimeoutError:
            result = SkillSandboxResult(
                skill_name=skill.name,
                status=SkillSandboxStatus.TIMEOUT,
                tier=manifest.tier,
                error=f"沙箱执行超时 (timeout_sec={manifest.resource_limits.timeout_sec})",
                manifest_fingerprint=fingerprint,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as exc:
            logger.exception("skill_sandbox 执行失败: %s", skill.name)
            result = SkillSandboxResult(
                skill_name=skill.name,
                status=SkillSandboxStatus.FAILED,
                tier=manifest.tier,
                error=str(exc),
                manifest_fingerprint=fingerprint,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        else:
            result.manifest_fingerprint = fingerprint
            if result.duration_ms == 0:
                result.duration_ms = int((time.monotonic() - started) * 1000)

        # 记账（无论成功失败都释放 in_flight；calls 仅成功累加）
        await _maybe_await_void(
            self.quota_tracker.record_usage(
                tenant_id=tenant_id or "_anonymous_",
                tier=manifest.tier,
                compute_ms=result.duration_ms,
                success=result.status == SkillSandboxStatus.SUCCESS,
            )
        )

        self._audit(result, user_id=user_id, tenant_id=tenant_id, trace_id=trace_id, gate=gate)
        return result

    # ------------------------------------------------------------------
    # T1: in-process
    # ------------------------------------------------------------------

    async def _run_in_process(
        self,
        skill: Skill,
        manifest: SandboxManifest,
        payload: dict[str, Any],
    ) -> SkillSandboxResult:
        """T1：直接 import + 调用 entrypoint。

        仅用于平台签名 skill；调用者负责保证函数行为可信。
        本方法仅做：
            - module/func 解析
            - sync/async 兼容调用
            - 强制 timeout（用 asyncio.wait_for）
        """
        assert manifest.entrypoint is not None
        module_name, func_name = manifest.entrypoint.split(":", 1)
        module = importlib.import_module(module_name)
        if not hasattr(module, func_name):
            raise RuntimeError(
                f"entrypoint {manifest.entrypoint!r} 未找到函数"
            )
        func = getattr(module, func_name)

        async def _call() -> Any:
            value = func(payload)
            if inspect.isawaitable(value):
                return await value
            return value

        output = await asyncio.wait_for(
            _call(),
            timeout=manifest.resource_limits.timeout_sec,
        )
        return SkillSandboxResult(
            skill_name=skill.name,
            status=SkillSandboxStatus.SUCCESS,
            tier=manifest.tier,
            output=output,
        )

    # ------------------------------------------------------------------
    # T2-T4: provider
    # ------------------------------------------------------------------

    async def _run_via_provider(
        self,
        skill: Skill,
        manifest: SandboxManifest,
        payload: dict[str, Any],
    ) -> SkillSandboxResult:
        """T2/T3/T4：走 SandboxProviderRegistry。

        本期只实装 T2（LocalProvider），T3/T4 走相同代码路径，
        但实际 provider 由 SandboxProviderRegistry 决定；docker/e2b provider 未就绪
        时会 raise，runner 把异常转成 FAILED。
        """
        provider_type = self._tier_to_provider.get(manifest.tier)
        if provider_type is None:
            raise RuntimeError(f"tier={manifest.tier.value} 未配置 provider")

        provider_cls = SandboxProviderRegistry.get(provider_type)
        provider = provider_cls()

        spec = self._build_spec(skill, manifest, payload)
        sandbox = await provider.provision(spec)
        try:
            cmd = self._build_command(manifest, payload)
            exec_result = await provider.exec(
                sandbox,
                cmd,
                timeout_sec=manifest.resource_limits.timeout_sec,
            )
        finally:
            try:
                await provider.terminate(sandbox)
            except Exception:
                logger.exception("provider.terminate 失败 skill=%s", skill.name)

        if exec_result.killed_by_timeout:
            return SkillSandboxResult(
                skill_name=skill.name,
                status=SkillSandboxStatus.TIMEOUT,
                tier=manifest.tier,
                error=exec_result.stderr or "killed by timeout",
                duration_ms=exec_result.duration_ms,
                metadata={"exit_code": exec_result.exit_code},
            )
        if not exec_result.succeeded:
            return SkillSandboxResult(
                skill_name=skill.name,
                status=SkillSandboxStatus.FAILED,
                tier=manifest.tier,
                error=exec_result.stderr or f"exit_code={exec_result.exit_code}",
                duration_ms=exec_result.duration_ms,
                metadata={"exit_code": exec_result.exit_code},
            )
        return SkillSandboxResult(
            skill_name=skill.name,
            status=SkillSandboxStatus.SUCCESS,
            tier=manifest.tier,
            output=exec_result.stdout,
            duration_ms=exec_result.duration_ms,
            metadata={"exit_code": exec_result.exit_code},
        )

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def _build_spec(
        self,
        skill: Skill,
        manifest: SandboxManifest,
        payload: dict[str, Any],
    ) -> SandboxSpec:
        """把 manifest 翻译成 sandbox_executor 的 SandboxSpec。"""
        return SandboxSpec(
            image=self._pick_image(manifest),
            env_vars={
                "ANXIN_SKILL_NAME": skill.name,
                "ANXIN_SKILL_VERSION": skill.version,
            },
            resource_limits=ResourceLimits(
                cpu_millicores=manifest.resource_limits.cpu_millicores,
                memory_mb=manifest.resource_limits.memory_mb,
                disk_mb=manifest.resource_limits.disk_mb,
            ),
            network_policy=NetworkPolicy(
                mode={
                    NetworkMode.NONE: NetworkPolicyMode.NONE,
                    NetworkMode.ALLOWLIST: NetworkPolicyMode.ALLOWLIST,
                    NetworkMode.FULL: NetworkPolicyMode.FULL,
                }[manifest.network.mode],
                allowed_hosts=list(manifest.network.allowed_hosts),
            ),
            timeout_sec=manifest.resource_limits.timeout_sec,
            metadata={
                "skill_name": skill.name,
                "skill_version": skill.version,
                "manifest_fingerprint": manifest.fingerprint(),
            },
        )

    @staticmethod
    def _pick_image(manifest: SandboxManifest) -> str:
        """根据 runtime 字段选基础镜像。"""
        runtime = (manifest.runtime or "python3.11").lower()
        if runtime.startswith("python"):
            ver = runtime.replace("python", "") or "3.11"
            return f"python:{ver}-slim"
        if runtime.startswith("node"):
            ver = runtime.replace("node", "") or "20"
            return f"node:{ver}-slim"
        return runtime

    @staticmethod
    def _build_command(
        manifest: SandboxManifest,
        payload: dict[str, Any],
    ) -> list[str]:
        """根据 entrypoint 生成执行命令（argv）。

        约定：runtime=pythonX → 执行 ``python -c "import M; print(M.F({...}))"``
        约定：runtime=nodeX  → 执行 ``node -e "require('M').F({...})"``

        payload 通过 stdin 注入更安全；但为简单起见暂时序列化进命令行。
        """
        assert manifest.entrypoint is not None
        module, func = manifest.entrypoint.split(":", 1)
        runtime = (manifest.runtime or "python3.11").lower()
        import json as _json
        payload_json = _json.dumps(payload, ensure_ascii=False, default=str)

        if runtime.startswith("python"):
            code = (
                f"import json, sys, {module} as _m;"
                f"_out=_m.{func}(json.loads(sys.argv[1]));"
                f"sys.stdout.write(json.dumps(_out, ensure_ascii=False, default=str))"
            )
            return ["python", "-c", code, payload_json]
        if runtime.startswith("node"):
            code = (
                f"const m=require('{module}');"
                f"const r=m.{func}(JSON.parse(process.argv[1]));"
                f"Promise.resolve(r).then(o=>process.stdout.write(JSON.stringify(o)))"
            )
            return ["node", "-e", code, payload_json]
        # 其他 runtime 留给后续扩展
        raise RuntimeError(f"暂不支持 runtime={runtime!r}")

    # ------------------------------------------------------------------
    # 审计
    # ------------------------------------------------------------------

    def _audit(
        self,
        result: SkillSandboxResult,
        *,
        user_id: str,
        tenant_id: str | None,
        trace_id: str | None,
        gate: PolicyGateResult | None = None,
    ) -> None:
        """把执行结果丢给 audit_hook。失败仅记日志。"""
        if self.audit_hook is None:
            return
        payload = {
            "event_type": "skill_sandbox_execute",
            "skill_name": result.skill_name,
            "tier": result.tier.value,
            "status": result.status.value,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "trace_id": trace_id,
            "duration_ms": result.duration_ms,
            "manifest_fingerprint": result.manifest_fingerprint,
            "error": result.error,
            "denied_reason": gate.reason if gate and not gate.allow else None,
        }
        try:
            self.audit_hook(payload)
        except Exception:
            logger.exception("skill_sandbox audit_hook 失败")


# ---------------------------------------------------------------------------
# QuotaTracker 适配 —— in-memory 同步 / Redis 异步两种实现都能用
# ---------------------------------------------------------------------------


async def _maybe_await_quota(value: Any):
    """check_and_reserve 既可能返回 QuotaDecision，也可能返回 Awaitable[QuotaDecision]。"""
    if inspect.isawaitable(value):
        return await value
    return value


async def _maybe_await_void(value: Any) -> None:
    """record_usage / release_reservation 同上，可能同步可能异步。"""
    if inspect.isawaitable(value):
        await value

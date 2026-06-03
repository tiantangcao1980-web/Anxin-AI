# -*- coding: utf-8 -*-
"""
SandboxManifest —— SKILL.md frontmatter 的沙箱声明

设计见 docs/v3/skills-sandbox-design.md §3。

frontmatter 例：

    sandbox:
      tier: T2
      entrypoint: pdf_extract:run
      runtime: python3.11
      resource_limits:
        cpu_millicores: 1000
        memory_mb: 512
        timeout_sec: 30
      network:
        mode: none
        allowed_hosts: []
      filesystem:
        read: ["/workspace/inputs"]
        write: ["/workspace/outputs"]
      permissions: [read:documents]
      egress_secrets: []

如果 ``sandbox`` 块缺省，默认按 **T0 prompt-only** 处理。
未声明 tier 但声明了 entrypoint —— 强制视为 T3（最严）。
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ManifestValidationError(ValueError):
    """SKILL.md.sandbox 字段非法。"""


class SandboxTier(str, Enum):
    """信任分级 —— 见 docs/v3/skills-sandbox-design.md §2。"""

    T0 = "T0"  # prompt-only：交给 SkillExecutor
    T1 = "T1"  # in-process：直接 import 调用
    T2 = "T2"  # subprocess：LocalProvider
    T3 = "T3"  # container：DockerProvider
    T4 = "T4"  # remote：E2B / CodexCloud

    @property
    def is_code(self) -> bool:
        """是否需要走代码执行通路（非 prompt-only）。"""
        return self != SandboxTier.T0

    @property
    def isolation_level(self) -> int:
        """越大越隔离，便于 fail-closed 时做降级判断。"""
        return {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}[self.value]


class NetworkMode(str, Enum):
    NONE = "none"
    ALLOWLIST = "allowlist"
    FULL = "full"  # 仅 dev


class ResourceLimitsManifest(BaseModel):
    cpu_millicores: int = Field(default=1000, ge=100, le=16000)
    memory_mb: int = Field(default=512, ge=64, le=65536)
    disk_mb: int = Field(default=1024, ge=128, le=102400)
    timeout_sec: int = Field(default=30, ge=1, le=3600)


class NetworkManifest(BaseModel):
    mode: NetworkMode = NetworkMode.NONE
    allowed_hosts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_allowlist(self) -> NetworkManifest:
        if self.mode == NetworkMode.ALLOWLIST and not self.allowed_hosts:
            raise ManifestValidationError(
                "network.mode=allowlist 必须提供 allowed_hosts"
            )
        if self.mode == NetworkMode.NONE and self.allowed_hosts:
            # 允许声明但语义上无效，提前报错以免误用
            raise ManifestValidationError(
                "network.mode=none 时不应同时声明 allowed_hosts"
            )
        return self


class FilesystemManifest(BaseModel):
    read: list[str] = Field(default_factory=list)
    write: list[str] = Field(default_factory=list)

    @field_validator("read", "write")
    @classmethod
    def _no_escape(cls, paths: list[str]) -> list[str]:
        cleaned: list[str] = []
        for p in paths:
            if not p:
                continue
            if ".." in p.split("/"):
                raise ManifestValidationError(f"路径不允许 ..: {p!r}")
            # 强制以 / 开头（沙箱内绝对路径），便于 audit
            normalized = str(PurePosixPath(p))
            if not normalized.startswith("/"):
                raise ManifestValidationError(f"路径必须是沙箱内绝对路径: {p!r}")
            cleaned.append(normalized)
        return cleaned


class SignatureManifest(BaseModel):
    algo: str = "ed25519"
    publisher: str
    sig: str


class SandboxManifest(BaseModel):
    """SKILL.md frontmatter 中 ``sandbox`` 块的解析结果。"""

    tier: SandboxTier = SandboxTier.T0
    entrypoint: str | None = None  # "module:func"
    runtime: str = "python3.11"
    resource_limits: ResourceLimitsManifest = Field(default_factory=ResourceLimitsManifest)
    network: NetworkManifest = Field(default_factory=NetworkManifest)
    filesystem: FilesystemManifest = Field(default_factory=FilesystemManifest)
    permissions: list[str] = Field(default_factory=list)
    egress_secrets: list[str] = Field(default_factory=list)
    signature: SignatureManifest | None = None

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _check_consistency(self) -> SandboxManifest:
        """跨字段一致性校验 —— 见设计文档 §3。"""
        # entrypoint 与 tier 必须配对
        if self.tier.is_code and not self.entrypoint:
            raise ManifestValidationError(
                f"tier={self.tier.value} 必须声明 entrypoint"
            )
        if not self.tier.is_code and self.entrypoint:
            raise ManifestValidationError(
                "T0 prompt-only skill 不应声明 entrypoint"
            )

        # T1 必须有签名
        if self.tier == SandboxTier.T1 and self.signature is None:
            raise ManifestValidationError(
                "tier=T1（in-process 受信）必须提供 signature"
            )

        # entrypoint 形如 "module:func"
        if self.entrypoint is not None:
            if ":" not in self.entrypoint:
                raise ManifestValidationError(
                    f"entrypoint 必须是 'module:func' 形式，得到 {self.entrypoint!r}"
                )
            mod, fn = self.entrypoint.split(":", 1)
            if not mod or not fn:
                raise ManifestValidationError(
                    f"entrypoint 模块与函数都不能为空，得到 {self.entrypoint!r}"
                )

        return self

    # ------------------------------------------------------------------
    # 工厂
    # ------------------------------------------------------------------

    @classmethod
    def from_frontmatter(cls, fm: dict[str, Any] | None) -> SandboxManifest:
        """从已解析的 frontmatter dict 构造 manifest。

        - ``fm`` 为 ``None`` / 不含 sandbox 块 → 默认 T0
        - ``fm`` 含 sandbox 但缺 tier → 隐含 T3（最严策略）
        """
        if not fm:
            return cls()
        raw = fm.get("sandbox")
        if raw is None:
            return cls()
        if not isinstance(raw, dict):
            raise ManifestValidationError("frontmatter.sandbox 必须是对象")

        data = dict(raw)
        # tier 缺省但声明了 entrypoint —— 设计文档默认 T3
        if "tier" not in data and data.get("entrypoint"):
            data["tier"] = SandboxTier.T3.value

        try:
            return cls.model_validate(data)
        except ManifestValidationError:
            raise
        except Exception as exc:
            raise ManifestValidationError(f"sandbox manifest 解析失败: {exc}") from exc

    # ------------------------------------------------------------------
    # 摘要
    # ------------------------------------------------------------------

    def fingerprint(self) -> str:
        """对 manifest 计算 sha256，用于安装时记录、运行期防篡改。

        ``model_dump(mode="json")`` 保证枚举值序列化稳定；按 key 排序后 hash。

        **重要**：fingerprint **不包含 signature 字段**，否则签发→校验形成自循环
        （签名落入 manifest 后会改变 fingerprint，导致校验自动失败）。
        """
        payload = self.model_dump(mode="json")
        payload.pop("signature", None)
        snapshot = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return "sha256:" + hashlib.sha256(snapshot.encode("utf-8")).hexdigest()

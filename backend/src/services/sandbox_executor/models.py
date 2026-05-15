"""
sandbox_executor.models —— 沙箱执行相关的数据模型

所有 Provider 共用的领域模型：
    - SandboxSpec        启动规格（image / env / mounts / 资源 / 网络 / 超时）
    - Sandbox            一个已启动沙箱的运行时句柄
    - ExecResult         单次命令执行结果
    - ResourceLimits     CPU / 内存 / 磁盘 限额
    - NetworkPolicy      网络出站策略

使用 Pydantic v2 BaseModel，便于序列化为 Celery / Redis / 事件流 payload。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------


class SandboxStatus(str, Enum):
    """沙箱生命周期状态。"""

    PENDING = "pending"  # 已创建 spec，未实际拉起
    PROVISIONING = "provisioning"  # 拉镜像 / 起容器中
    RUNNING = "running"  # 可接受 exec
    TERMINATED = "terminated"  # 正常清理完毕
    FAILED = "failed"  # 启动或运行失败


class NetworkPolicyMode(str, Enum):
    """沙箱网络出站策略。"""

    NONE = "none"  # 完全断网（最安全，默认）
    ALLOWLIST = "allowlist"  # 仅放行 allowed_hosts 中的域名/IP
    FULL = "full"  # 完全放开（仅本地开发用）


# ---------------------------------------------------------------------------
# 资源 / 网络
# ---------------------------------------------------------------------------


class ResourceLimits(BaseModel):
    """单沙箱的资源上限。"""

    cpu_millicores: int = Field(default=1000, ge=100, le=16000, description="CPU 配额，1000 = 1 核")
    memory_mb: int = Field(default=512, ge=64, le=65536, description="内存上限（MB）")
    disk_mb: int = Field(default=2048, ge=128, le=102400, description="临时磁盘上限（MB）")


class NetworkPolicy(BaseModel):
    """出站网络策略。"""

    mode: NetworkPolicyMode = NetworkPolicyMode.NONE
    allowed_hosts: list[str] = Field(
        default_factory=list, description="ALLOWLIST 模式下放行的域名/IP"
    )


# ---------------------------------------------------------------------------
# 启动规格 + 运行时句柄
# ---------------------------------------------------------------------------


class SandboxSpec(BaseModel):
    """沙箱启动规格（不可变）。

    Provider 根据该 spec 决定如何拉起隔离环境。
    """

    image: str = Field(
        default="python:3.11-slim", description="容器镜像或运行时标识；LocalProvider 忽略"
    )
    env_vars: dict[str, str] = Field(default_factory=dict, description="注入到沙箱内的环境变量")
    mounts: dict[str, str] = Field(
        default_factory=dict,
        description="宿主机路径 → 沙箱内路径 映射（如 worktree → /workspace）",
    )
    network_policy: NetworkPolicy = Field(default_factory=NetworkPolicy)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)
    timeout_sec: int = Field(default=300, ge=1, le=3600, description="单次 exec 默认超时（秒）")
    workdir: str = Field(default="/workspace", description="exec 默认工作目录")
    metadata: dict[str, Any] = Field(default_factory=dict, description="任意附加上下文，如 task_id")


class Sandbox(BaseModel):
    """一个已 provision 出来的沙箱运行时句柄。

    Provider 将其返回给上层调度器；后续 exec/upload/download/terminate
    都需要传回该对象。
    """

    id: str = Field(default_factory=lambda: f"sbx_{uuid.uuid4().hex[:16]}")
    provider_type: str = Field(..., description="对应的 Provider.provider_type")
    status: SandboxStatus = SandboxStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    spec: SandboxSpec
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Provider 私有状态，如 container_id / workdir"
    )


# ---------------------------------------------------------------------------
# 命令执行结果
# ---------------------------------------------------------------------------


class ExecResult(BaseModel):
    """一次沙箱内命令的执行结果。"""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0
    killed_by_timeout: bool = False
    cmd: list[str] = Field(default_factory=list, description="实际执行的命令（便于审计）")

    @property
    def succeeded(self) -> bool:
        """语义糖：exit_code == 0 且未被超时杀掉。"""
        return self.exit_code == 0 and not self.killed_by_timeout


__all__ = [
    "ExecResult",
    "NetworkPolicy",
    "NetworkPolicyMode",
    "ResourceLimits",
    "Sandbox",
    "SandboxSpec",
    "SandboxStatus",
]

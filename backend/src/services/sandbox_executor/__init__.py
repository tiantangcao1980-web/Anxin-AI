# -*- coding: utf-8 -*-
"""
sandbox_executor —— V3 沙箱执行器骨架（P3-E）

提供统一的沙箱执行抽象，未来可插入不同 Provider：
    - LocalProvider       —— 本地 subprocess（开发/测试，唯一实装）
    - DockerProvider      —— 容器隔离（P5/P6 实装）
    - E2BProvider         —— E2B 云沙箱（占位）
    - CodexCloudProvider  —— Codex Cloud（占位）

设计参考：
    - Codex Cloud 的远程任务沙箱
    - Claude Dispatch 的 worktree-per-task 模型

⚠️ 本模块只暴露接口与 LocalProvider 实装，不与 task_orchestrator 直接耦合。
   P5 阶段会在 task_orchestrator/worker.py 中通过 SandboxProviderRegistry.default()
   切换 worker 的执行环境。
"""

from src.services.sandbox_executor.base import BaseSandboxProvider
from src.services.sandbox_executor.config import get_sandbox_settings
from src.services.sandbox_executor.docker_provider import (
    DockerNotAvailable,
    DockerProvider,
)
from src.services.sandbox_executor.local_provider import LocalProvider
from src.services.sandbox_executor.models import (
    ExecResult,
    NetworkPolicy,
    NetworkPolicyMode,
    ResourceLimits,
    Sandbox,
    SandboxSpec,
    SandboxStatus,
)
from src.services.sandbox_executor.registry import SandboxProviderRegistry

__all__ = [
    "BaseSandboxProvider",
    "DockerNotAvailable",
    "DockerProvider",
    "ExecResult",
    "LocalProvider",
    "NetworkPolicy",
    "NetworkPolicyMode",
    "ResourceLimits",
    "Sandbox",
    "SandboxProviderRegistry",
    "SandboxSpec",
    "SandboxStatus",
    "get_sandbox_settings",
]

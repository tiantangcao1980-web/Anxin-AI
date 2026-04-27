# -*- coding: utf-8 -*-
"""
sandbox_executor.codex_cloud_provider —— Codex Cloud Provider（占位）

参考：OpenAI Codex Cloud / Anthropic Claude Dispatch 的远程任务沙箱模式。

预期形态：
    - 远程托管沙箱集群，REST/WebSocket API 控制
    - provision = POST /sandboxes（带镜像 + worktree URL）
    - exec      = POST /sandboxes/{id}/exec（流式）
    - 网络隔离  = 平台侧默认 deny-all，通过 allowlist 白名单控制
    - 心跳/超时 = 平台侧管理，本地 worker 仅订阅事件

待 P 后续接入正式 SaaS 时实装；当前占位以便 Registry 注册。
"""

from __future__ import annotations

from typing import AsyncIterator, ClassVar, Optional

from src.services.sandbox_executor.base import BaseSandboxProvider
from src.services.sandbox_executor.models import ExecResult, Sandbox, SandboxSpec


class CodexCloudProvider(BaseSandboxProvider):
    """Codex Cloud 远程沙箱 Provider（占位）。"""

    provider_type: ClassVar[str] = "codex_cloud"

    async def provision(self, spec: SandboxSpec) -> Sandbox:
        raise NotImplementedError("CodexCloudProvider.provision: 后续接入实装")

    async def exec(
        self,
        sandbox: Sandbox,
        cmd: list[str],
        stdin: Optional[bytes] = None,
        timeout_sec: Optional[int] = None,
    ) -> ExecResult:
        raise NotImplementedError("CodexCloudProvider.exec: 后续接入实装")

    async def upload(self, sandbox: Sandbox, src_path: str, dst_path: str) -> None:
        raise NotImplementedError("CodexCloudProvider.upload: 后续接入实装")

    async def download(self, sandbox: Sandbox, sandbox_path: str) -> bytes:
        raise NotImplementedError("CodexCloudProvider.download: 后续接入实装")

    def stream_logs(self, sandbox: Sandbox) -> AsyncIterator[str]:
        raise NotImplementedError("CodexCloudProvider.stream_logs: 后续接入实装")

    async def terminate(self, sandbox: Sandbox) -> None:
        raise NotImplementedError("CodexCloudProvider.terminate: 后续接入实装")


__all__ = ["CodexCloudProvider"]

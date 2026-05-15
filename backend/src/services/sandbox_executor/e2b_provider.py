"""
sandbox_executor.e2b_provider —— E2B 云沙箱 Provider（占位）

E2B (https://e2b.dev) 是托管的 LLM-friendly 代码执行沙箱：
    - SDK：     e2b / e2b-code-interpreter (Python)
    - 隔离：    每会话一个 Firecracker microVM
    - 网络：    可控（默认开放，可通过 firewall 配置）
    - 文件：    SDK 提供 filesystem.write/read，原生支持文件挂载
    - 流式：    process.stdout / .stderr 是 async iterator

适用场景：
    - 不想自维护 Docker 集群
    - 需要快速冷启动（<300ms）
    - 法律工具调用大模型生成的代码（强隔离需求）

待 P 后续按需实装；当前只占位以便 Registry 注册。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import ClassVar

from src.services.sandbox_executor.base import BaseSandboxProvider
from src.services.sandbox_executor.models import ExecResult, Sandbox, SandboxSpec


class E2BProvider(BaseSandboxProvider):
    """E2B 云沙箱 Provider（占位）。"""

    provider_type: ClassVar[str] = "e2b"

    async def provision(self, spec: SandboxSpec) -> Sandbox:
        raise NotImplementedError("E2BProvider.provision: 后续按需实装")

    async def exec(
        self,
        sandbox: Sandbox,
        cmd: list[str],
        stdin: bytes | None = None,
        timeout_sec: int | None = None,
    ) -> ExecResult:
        raise NotImplementedError("E2BProvider.exec: 后续按需实装")

    async def upload(self, sandbox: Sandbox, src_path: str, dst_path: str) -> None:
        raise NotImplementedError("E2BProvider.upload: 后续按需实装")

    async def download(self, sandbox: Sandbox, sandbox_path: str) -> bytes:
        raise NotImplementedError("E2BProvider.download: 后续按需实装")

    def stream_logs(self, sandbox: Sandbox) -> AsyncIterator[str]:
        raise NotImplementedError("E2BProvider.stream_logs: 后续按需实装")

    async def terminate(self, sandbox: Sandbox) -> None:
        raise NotImplementedError("E2BProvider.terminate: 后续按需实装")


__all__ = ["E2BProvider"]

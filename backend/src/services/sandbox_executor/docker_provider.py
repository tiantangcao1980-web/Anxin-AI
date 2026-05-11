# -*- coding: utf-8 -*-
"""
sandbox_executor.docker_provider —— DockerProvider（P5/P6 实装占位）

⚠️ 当前所有方法均 raise NotImplementedError，仅占位以便 Registry 注册和 mypy 检查。

实装方案（待 P5 完成）：

    依赖：    docker-py (sync) 或 aiodocker (async)
    隔离：    每个 task 一个容器，--rm 自动清理；--network=none 默认断网
    挂载：    spec.mounts → -v host_path:container_path:ro|rw
              典型：git worktree → /workspace（可写），密钥目录 → /etc/secrets:ro
    资源：    --cpus / --memory / --memory-swap / --pids-limit / --read-only
    用户：    --user 1000:1000 + --cap-drop ALL --security-opt no-new-privileges
    超时：    container.exec_run 配合 wait_timeout 或 docker exec --timeout
    日志：    container.logs(stream=True, follow=True) → AsyncIterator[str]
    清理：    terminate 调 container.remove(force=True)，幂等

P3 阶段先确定接口形状，P5 真正接入 task_orchestrator 时再实装。
"""

from __future__ import annotations

from typing import AsyncIterator, ClassVar, Optional

from src.services.sandbox_executor.base import BaseSandboxProvider
from src.services.sandbox_executor.models import ExecResult, Sandbox, SandboxSpec


class DockerProvider(BaseSandboxProvider):
    """基于 Docker 容器的隔离 Provider（占位）。"""

    provider_type: ClassVar[str] = "docker"

    async def provision(self, spec: SandboxSpec) -> Sandbox:
        """P5/P6 实装：docker pull → docker create → docker start → 挂载 worktree。"""
        raise NotImplementedError("DockerProvider.provision: P5/P6 实装")

    async def exec(
        self,
        sandbox: Sandbox,
        cmd: list[str],
        stdin: Optional[bytes] = None,
        timeout_sec: Optional[int] = None,
    ) -> ExecResult:
        """P5/P6 实装：container.exec_run(cmd, stdin, demux=True)。"""
        raise NotImplementedError("DockerProvider.exec: P5/P6 实装")

    async def upload(self, sandbox: Sandbox, src_path: str, dst_path: str) -> None:
        """P5/P6 实装：put_archive 或 docker cp。"""
        raise NotImplementedError("DockerProvider.upload: P5/P6 实装")

    async def download(self, sandbox: Sandbox, sandbox_path: str) -> bytes:
        """P5/P6 实装：get_archive + tar 解包。"""
        raise NotImplementedError("DockerProvider.download: P5/P6 实装")

    def stream_logs(self, sandbox: Sandbox) -> AsyncIterator[str]:
        """P5/P6 实装：container.logs(stream=True, follow=True)。"""
        raise NotImplementedError("DockerProvider.stream_logs: P5/P6 实装")

    async def terminate(self, sandbox: Sandbox) -> None:
        """P5/P6 实装：container.remove(force=True)，幂等。"""
        raise NotImplementedError("DockerProvider.terminate: P5/P6 实装")


__all__ = ["DockerProvider"]

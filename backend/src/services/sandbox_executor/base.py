# -*- coding: utf-8 -*-
"""
sandbox_executor.base —— 沙箱 Provider 抽象基类

所有具体实现（Local / Docker / E2B / CodexCloud）必须实现以下方法：

    provision(spec)        启动沙箱，返回 Sandbox 句柄
    exec(sandbox, cmd)     在沙箱内执行命令，返回 ExecResult
    upload(sandbox, ...)   宿主机 → 沙箱 文件传输
    download(sandbox, ...) 沙箱 → 宿主机 文件读取
    stream_logs(sandbox)   异步日志流（行）
    terminate(sandbox)     清理资源（容器/临时目录/远程实例）

设计原则：
    - 全异步（async / AsyncIterator），匹配 task_orchestrator 的 asyncio worker
    - Provider 不直接持有 Sandbox 状态，状态在返回的 Sandbox 模型里；
      多次调用同一个沙箱，由调用方传回 Sandbox 句柄
    - terminate 必须幂等：重复调用不报错
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, ClassVar, Optional

from src.services.sandbox_executor.models import (
    ExecResult,
    Sandbox,
    SandboxSpec,
)


class BaseSandboxProvider(ABC):
    """沙箱 Provider 抽象基类。

    子类必须设置 ``provider_type`` 类属性，作为 SandboxProviderRegistry 的注册键。
    """

    provider_type: ClassVar[str] = ""

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    @abstractmethod
    async def provision(self, spec: SandboxSpec) -> Sandbox:
        """根据 spec 启动一个沙箱。

        实现职责：
            1. 校验 spec（镜像可用 / 资源足够）
            2. 拉镜像 / 起容器 / mkdir 临时目录
            3. 挂载 spec.mounts（如 git worktree → /workspace）
            4. 注入 spec.env_vars
            5. 应用 spec.resource_limits / spec.network_policy
            6. 返回 status=RUNNING 的 Sandbox

        失败时应抛出异常，且不留下残留资源。
        """

    @abstractmethod
    async def terminate(self, sandbox: Sandbox) -> None:
        """清理沙箱资源。必须幂等。"""

    # ------------------------------------------------------------------
    # 命令执行
    # ------------------------------------------------------------------

    @abstractmethod
    async def exec(
        self,
        sandbox: Sandbox,
        cmd: list[str],
        stdin: Optional[bytes] = None,
        timeout_sec: Optional[int] = None,
    ) -> ExecResult:
        """在沙箱内执行命令。

        参数：
            sandbox      由 provision 返回的句柄
            cmd          命令 argv 列表（绝不接受 shell 字符串，防止注入）
            stdin        可选标准输入字节流
            timeout_sec  覆盖 spec.timeout_sec

        返回：
            ExecResult（含 stdout/stderr/exit_code/duration_ms/killed_by_timeout）

        实现要求：
            - 一律 argv 列表，禁止 shell=True / shell expansion
            - 超时必须真正杀进程（包括子进程组）
            - stdout/stderr 应有大小上限，防止 OOM
        """

    # ------------------------------------------------------------------
    # 文件传输
    # ------------------------------------------------------------------

    @abstractmethod
    async def upload(self, sandbox: Sandbox, src_path: str, dst_path: str) -> None:
        """上传宿主机文件到沙箱内。

        参数：
            src_path  宿主机绝对路径
            dst_path  沙箱内绝对路径（相对 spec.workdir 也可，由实现约定）
        """

    @abstractmethod
    async def download(self, sandbox: Sandbox, sandbox_path: str) -> bytes:
        """从沙箱内下载文件，返回字节内容。

        小文件用；大文件应使用 stream API（未来扩展）。
        """

    # ------------------------------------------------------------------
    # 日志流
    # ------------------------------------------------------------------

    @abstractmethod
    def stream_logs(self, sandbox: Sandbox) -> AsyncIterator[str]:
        """异步迭代沙箱内进程的实时日志（行）。

        典型用法：
            async for line in provider.stream_logs(sbx):
                publish_to_event_stream(line)
        """


__all__ = ["BaseSandboxProvider"]

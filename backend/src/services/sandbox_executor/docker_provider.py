# -*- coding: utf-8 -*-
"""
sandbox_executor.docker_provider —— Docker 容器隔离 Provider

设计要点（docs/v3/skills-sandbox-design.md §2 / §6 / §7）：

    1. **每次 exec 一个 ephemeral 容器**：``docker run --rm``，
       无需追踪长生命周期 container_id；与 LocalProvider 用法对齐。
    2. **默认强隔离**：
        - ``--network=none``（除非 manifest 允许，allowlist 见 P3 iptables）
        - ``--read-only`` 根文件系统只读
        - ``--cap-drop=ALL`` 丢弃所有 Linux capability
        - ``--security-opt=no-new-privileges``
        - ``--user=65534:65534`` 以 nobody 运行
        - ``--pids-limit=256``
        - ``--memory=<spec>m`` / ``--cpus=<spec>`` / ``--memory-swap=<spec>m``
        - ``--tmpfs /tmp``（受 disk_mb 控制）
    3. **不依赖 docker-py / aiodocker**：通过 ``docker`` CLI + ``asyncio.create_subprocess_exec``，
       避免新增 PyPI 依赖；命令构造可单测。
    4. **workdir 隔离**：每次 provision 在宿主 ``/tmp/sbx_docker_*`` 建临时目录，
       通过 ``-v workdir:/workspace`` 挂载到容器内 ``/workspace``。
       terminate 删宿主目录。
    5. **超时**：宿主进程 ``asyncio.wait_for`` + ``docker kill <name>`` 兜底。

⚠️ 仍依赖 dockerd；在无 docker 的环境 ``provision/exec`` 会抛 ``DockerNotAvailable``。
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import AsyncIterator, ClassVar, Optional

from loguru import logger

from src.services.sandbox_executor.base import BaseSandboxProvider
from src.services.sandbox_executor.models import (
    ExecResult,
    NetworkPolicyMode,
    Sandbox,
    SandboxSpec,
    SandboxStatus,
)


class DockerNotAvailable(RuntimeError):
    """docker CLI 不存在或 daemon 不可达。"""


# stdout / stderr 截断保护
_MAX_OUTPUT_BYTES = 10 * 1024 * 1024


class DockerProvider(BaseSandboxProvider):
    """Docker 容器 Provider（默认严格隔离）。

    Sandbox.metadata 约定：
        - workdir          宿主机临时目录（绝对路径）
        - container_name   预生成的容器名（``anxin-sbx-<id>``）；exec 时使用
        - image            实际使用的镜像（resolve image 后写入）
    """

    provider_type: ClassVar[str] = "docker"

    DEFAULT_USER: ClassVar[str] = "65534:65534"
    DEFAULT_TMPFS_SIZE_MB: ClassVar[int] = 64

    def __init__(self, *, docker_bin: str = "docker") -> None:
        self.docker_bin = docker_bin

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def provision(self, spec: SandboxSpec) -> Sandbox:
        """创建宿主 workdir + 提前生成容器名；不在此 step 启动容器。

        真正的容器在 ``exec`` 中按 ephemeral 模式启动并立刻清理。
        """
        await self._require_docker()
        workdir = tempfile.mkdtemp(prefix="sbx_docker_")
        # 给沙箱进程的输出目录
        Path(workdir, "outputs").mkdir(exist_ok=True)
        Path(workdir, "inputs").mkdir(exist_ok=True)

        sandbox = Sandbox(
            provider_type=self.provider_type,
            status=SandboxStatus.RUNNING,
            spec=spec,
            metadata={
                "workdir": workdir,
                "container_name": f"anxin-sbx-{uuid.uuid4().hex[:12]}",
                "image": spec.image,
            },
        )
        logger.info(
            f"[DockerProvider] provisioned sandbox={sandbox.id} workdir={workdir} image={spec.image}"
        )
        return sandbox

    async def terminate(self, sandbox: Sandbox) -> None:
        """删宿主 workdir + 兜底 ``docker rm -f``（容器若残留）。幂等。"""
        workdir = sandbox.metadata.get("workdir")
        container_name = sandbox.metadata.get("container_name")

        if container_name:
            # 兜底清理
            try:
                proc = await asyncio.create_subprocess_exec(
                    self.docker_bin, "rm", "-f", container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.wait(), timeout=10)
            except Exception:
                # 容器本来就不存在是常态
                pass

        if workdir and os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)
            logger.info(f"[DockerProvider] terminated sandbox={sandbox.id} workdir={workdir}")
        sandbox.status = SandboxStatus.TERMINATED

    # ------------------------------------------------------------------
    # 命令执行
    # ------------------------------------------------------------------

    async def exec(
        self,
        sandbox: Sandbox,
        cmd: list[str],
        stdin: Optional[bytes] = None,
        timeout_sec: Optional[int] = None,
    ) -> ExecResult:
        """启动一个 ephemeral 容器执行 cmd，自动清理。"""
        await self._require_docker()
        self._validate_cmd(cmd)

        workdir = sandbox.metadata.get("workdir")
        if not workdir or not os.path.isdir(workdir):
            raise RuntimeError(f"sandbox={sandbox.id} workdir 不可用")

        container_name = sandbox.metadata.get("container_name")
        timeout = timeout_sec if timeout_sec is not None else sandbox.spec.timeout_sec

        docker_args = self.build_docker_args(
            spec=sandbox.spec,
            workdir=workdir,
            container_name=container_name,
            cmd=cmd,
        )
        full_argv = [self.docker_bin, *docker_args]

        start = time.monotonic()
        killed = False
        proc = await asyncio.create_subprocess_exec(
            *full_argv,
            stdin=asyncio.subprocess.PIPE if stdin is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(input=stdin),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            killed = True
            # docker kill 比 SIGKILL host 进程更可靠
            try:
                kill_proc = await asyncio.create_subprocess_exec(
                    self.docker_bin, "kill", container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(kill_proc.wait(), timeout=5)
            except Exception:
                pass
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=5
                )
            except asyncio.TimeoutError:
                stdout_b, stderr_b = b"", b""
            logger.warning(
                f"[DockerProvider] exec timeout killed sandbox={sandbox.id} timeout={timeout}s"
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            stdout=_safe_decode(stdout_b),
            stderr=_safe_decode(stderr_b),
            exit_code=proc.returncode if proc.returncode is not None else -1,
            duration_ms=duration_ms,
            killed_by_timeout=killed,
            cmd=list(cmd),
        )

    # ------------------------------------------------------------------
    # 文件传输
    # ------------------------------------------------------------------

    async def upload(self, sandbox: Sandbox, src_path: str, dst_path: str) -> None:
        """直接 copy 到宿主 workdir/inputs；容器启动后已通过 -v 可见。"""
        workdir = sandbox.metadata.get("workdir")
        if not workdir:
            raise RuntimeError(f"sandbox={sandbox.id} workdir 不可用")
        # 规范化 dst_path：去掉前导 / 和容器路径前缀 /workspace
        rel = dst_path.lstrip("/")
        if rel.startswith("workspace/"):
            rel = rel[len("workspace/"):]
        target = Path(workdir) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, target)

    async def download(self, sandbox: Sandbox, sandbox_path: str) -> bytes:
        """从宿主 workdir 读取（容器写到 /workspace 对应宿主 workdir）。"""
        workdir = sandbox.metadata.get("workdir")
        if not workdir:
            raise RuntimeError(f"sandbox={sandbox.id} workdir 不可用")
        rel = sandbox_path.lstrip("/")
        if rel.startswith("workspace/"):
            rel = rel[len("workspace/"):]
        source = Path(workdir) / rel
        if not source.is_file():
            raise FileNotFoundError(f"沙箱内文件不存在: {sandbox_path}")
        return source.read_bytes()

    # ------------------------------------------------------------------
    # 日志流（占位）
    # ------------------------------------------------------------------

    async def stream_logs(self, sandbox: Sandbox) -> AsyncIterator[str]:
        """``docker logs -f`` 流式输出。

        当前用 ``--rm`` 一次性容器，logs 在 exec 完后即销毁；
        如果未来切换到长生命周期容器（``docker run -d``），这里可改为 ``docker logs -f``。
        """
        if False:  # pragma: no cover - placeholder generator
            yield ""
        raise NotImplementedError(
            "DockerProvider.stream_logs: ephemeral 模式无持久日志，请直接读 exec 的 stdout/stderr"
        )

    # ------------------------------------------------------------------
    # 命令拼装（公开，便于单测）
    # ------------------------------------------------------------------

    def build_docker_args(
        self,
        *,
        spec: SandboxSpec,
        workdir: str,
        container_name: str,
        cmd: list[str],
    ) -> list[str]:
        """根据 spec 生成 ``docker run ...`` 的 argv 列表（不含 ``docker``）。

        分离这个函数是为了：
            - 单测可断言安全参数都在
            - 未来切到 docker SDK 时只换 transport
        """
        rl = spec.resource_limits
        net = spec.network_policy

        args: list[str] = [
            "run",
            "--rm",
            "--name", container_name,
            # ---- 安全 ----
            "--user", self.DEFAULT_USER,
            "--cap-drop=ALL",
            "--security-opt", "no-new-privileges",
            "--read-only",
            # tmpfs 给 /tmp，但限制大小防爆盘
            "--tmpfs", f"/tmp:size={self.DEFAULT_TMPFS_SIZE_MB}m,mode=1777",
            "--pids-limit", "256",
            # ---- 资源 ----
            "--memory", f"{rl.memory_mb}m",
            "--memory-swap", f"{rl.memory_mb}m",  # 禁用 swap
            "--cpus", f"{rl.cpu_millicores / 1000:.3f}",
            # ---- 网络 ----
            *self._network_args(net.mode),
            # ---- 文件系统挂载 ----
            "-v", f"{workdir}:/workspace:rw",
            "-w", "/workspace",
            # ---- 环境 ----
        ]
        # spec.env_vars 注入（用 -e KEY=VALUE）
        for k, v in spec.env_vars.items():
            args += ["-e", f"{k}={v}"]
        # spec.mounts（额外目录挂载）—— 用 :ro 挂载，安全默认
        for host_path, container_path in spec.mounts.items():
            args += ["-v", f"{host_path}:{container_path}:ro"]

        # 镜像 + 命令
        image = spec.image or "python:3.11-slim"
        args += [image, *cmd]
        return args

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @staticmethod
    def _network_args(mode: NetworkPolicyMode) -> list[str]:
        """把 NetworkPolicyMode 翻译成 docker run 的网络参数。

        当前实装：
            NONE      -> ``--network=none``
            ALLOWLIST -> 退化到 ``--network=none``（iptables egress 留 P3）
            FULL      -> ``--network=bridge``（仅 dev）
        """
        if mode == NetworkPolicyMode.FULL:
            return ["--network", "bridge"]
        # NONE 与 ALLOWLIST 都先按 none 处理；allowlist 需要预创建 user-defined network
        # + iptables 出站规则，留给 P3
        return ["--network", "none"]

    @staticmethod
    def _validate_cmd(cmd: list[str]) -> None:
        """与 LocalProvider 同样的最小校验。"""
        if not cmd:
            raise ValueError("cmd 不能为空")
        if not isinstance(cmd, list):
            raise TypeError("cmd 必须是 list[str]")
        for arg in cmd:
            if not isinstance(arg, str):
                raise TypeError(f"cmd 元素必须是 str: {arg!r}")
            if "\x00" in arg:
                raise ValueError("cmd 含 NUL 字节，拒绝执行")

    async def _require_docker(self) -> None:
        """启动前检查 docker daemon 是否可用；失败抛 DockerNotAvailable。"""
        if shutil.which(self.docker_bin) is None:
            raise DockerNotAvailable(f"docker 可执行文件不存在: {self.docker_bin}")
        try:
            proc = await asyncio.create_subprocess_exec(
                self.docker_bin, "version", "--format", "{{.Server.Version}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        except Exception as exc:
            raise DockerNotAvailable(f"docker daemon 不可达: {exc}") from exc
        if proc.returncode != 0 or not stdout_b.strip():
            raise DockerNotAvailable("docker daemon 未运行或权限不足")


def _safe_decode(b: bytes | None) -> str:
    if not b:
        return ""
    truncated = b[:_MAX_OUTPUT_BYTES]
    return truncated.decode("utf-8", errors="replace")


__all__ = ["DockerNotAvailable", "DockerProvider"]

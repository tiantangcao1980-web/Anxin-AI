# -*- coding: utf-8 -*-
"""
sandbox_executor.local_provider —— LocalProvider（subprocess 实装）

⚠️ 仅用于本地开发与单元测试，**不提供任何安全隔离**：
    - 进程跑在宿主机用户身份下
    - 文件系统、网络、内核与宿主共享
    - 不要在生产环境使用！

P5/P6 之前用它配合 task_orchestrator 跑通流水线即可；
正式生产请切换 DockerProvider / E2BProvider。

安全防护（即便是开发环境也保留）：
    1. cmd 必须是 list[str]，禁止 shell=True，从源头防 shell injection
    2. 拒绝包含 NUL 字节的参数（防止某些 libc 截断攻击）
    3. 临时目录使用 tempfile.mkdtemp(prefix="sbx_")，不可被预测路径覆盖
    4. 默认 cwd = 沙箱临时目录，避免误操作宿主项目目录
    5. 超时通过 process.kill() + wait 强制结束（而非软 SIGTERM 后撒手）
    6. exec 的 cwd 不允许逃逸出沙箱目录（基础校验）
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import AsyncIterator, ClassVar, Optional

from loguru import logger

from src.services.sandbox_executor.base import BaseSandboxProvider
from src.services.sandbox_executor.models import (
    ExecResult,
    Sandbox,
    SandboxSpec,
    SandboxStatus,
)


# 限制 stdout/stderr 单次抓取上限，防止 OOM
_MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10MB


class LocalProvider(BaseSandboxProvider):
    """本地 subprocess Provider。

    元数据约定（写入 ``Sandbox.metadata``）：
        - workdir: 沙箱临时根目录（绝对路径）
        - spec_file: spec.json 落盘路径
    """

    provider_type: ClassVar[str] = "local"

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def provision(self, spec: SandboxSpec) -> Sandbox:
        """创建临时目录 + 落盘 spec.json，返回 RUNNING 状态的 Sandbox。"""
        workdir = tempfile.mkdtemp(prefix="sbx_local_")
        spec_path = Path(workdir) / "spec.json"
        try:
            spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
        except Exception:
            # 任何异常都要保证不留垃圾
            shutil.rmtree(workdir, ignore_errors=True)
            raise

        sandbox = Sandbox(
            provider_type=self.provider_type,
            status=SandboxStatus.RUNNING,
            spec=spec,
            metadata={
                "workdir": workdir,
                "spec_file": str(spec_path),
            },
        )
        logger.info(f"[LocalProvider] provisioned sandbox={sandbox.id} workdir={workdir}")
        return sandbox

    async def terminate(self, sandbox: Sandbox) -> None:
        """删除沙箱临时目录。幂等：目录不存在不报错。"""
        workdir = sandbox.metadata.get("workdir")
        if workdir and os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)
            logger.info(f"[LocalProvider] terminated sandbox={sandbox.id} workdir={workdir}")
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
        """通过 ``asyncio.create_subprocess_exec`` 执行命令（无 shell）。"""
        self._validate_cmd(cmd)
        workdir = sandbox.metadata.get("workdir")
        if not workdir or not os.path.isdir(workdir):
            raise RuntimeError(f"sandbox={sandbox.id} workdir 不可用，可能已被 terminate")

        timeout = timeout_sec if timeout_sec is not None else sandbox.spec.timeout_sec
        env = {**os.environ, **sandbox.spec.env_vars}

        start = time.monotonic()
        killed = False
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workdir,
            env=env,
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
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            # 收尾
            try:
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=5)
            except asyncio.TimeoutError:
                stdout_b, stderr_b = b"", b""
            logger.warning(
                f"[LocalProvider] exec timeout killed sandbox={sandbox.id} cmd={cmd[:3]} timeout={timeout}s"
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
        """宿主机 → 沙箱临时目录。dst_path 相对沙箱 workdir 解析。"""
        workdir = self._require_workdir(sandbox)
        full_dst = self._resolve_inside(workdir, dst_path)
        full_dst.parent.mkdir(parents=True, exist_ok=True)
        # shutil.copy 同步阻塞，包一层 to_thread
        await asyncio.to_thread(shutil.copy, src_path, str(full_dst))

    async def download(self, sandbox: Sandbox, sandbox_path: str) -> bytes:
        """读取沙箱内文件字节。sandbox_path 相对 workdir 解析。"""
        workdir = self._require_workdir(sandbox)
        full = self._resolve_inside(workdir, sandbox_path)
        return await asyncio.to_thread(full.read_bytes)

    # ------------------------------------------------------------------
    # 日志流（占位实装：把 spec.json 一行一行吐出，便于上层调通流式管道）
    # ------------------------------------------------------------------

    async def stream_logs(self, sandbox: Sandbox) -> AsyncIterator[str]:
        """LocalProvider 没有持久 daemon，这里返回 spec 摘要作为占位日志。

        真正的日志流应在 exec 流式输出场景实装；当前骨架仅保证接口可用。
        """

        async def _gen() -> AsyncIterator[str]:
            yield f"[LocalProvider] sandbox={sandbox.id} status={sandbox.status}"
            yield f"[LocalProvider] workdir={sandbox.metadata.get('workdir')}"
            yield f"[LocalProvider] spec={json.dumps(sandbox.spec.model_dump(mode='json'), ensure_ascii=False)[:200]}"

        return _gen()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_cmd(cmd: list[str]) -> None:
        """命令安全校验：必须是非空列表，每项是字符串且不含 NUL。"""
        if not isinstance(cmd, list) or not cmd:
            raise ValueError("cmd 必须是非空 list[str]")
        for i, arg in enumerate(cmd):
            if not isinstance(arg, str):
                raise TypeError(f"cmd[{i}] 必须是 str，得到 {type(arg).__name__}")
            if "\x00" in arg:
                raise ValueError(f"cmd[{i}] 包含非法 NUL 字节")

    @staticmethod
    def _require_workdir(sandbox: Sandbox) -> Path:
        workdir = sandbox.metadata.get("workdir")
        if not workdir or not os.path.isdir(workdir):
            raise RuntimeError(f"sandbox={sandbox.id} workdir 不可用")
        return Path(workdir)

    @staticmethod
    def _resolve_inside(workdir: Path, rel_or_abs: str) -> Path:
        """把目标路径解析到 workdir 内，禁止 .. 逃逸。"""
        if not rel_or_abs:
            raise ValueError("路径不能为空")
        # 相对路径相对 workdir，绝对路径若不在 workdir 内则拒绝
        candidate = Path(rel_or_abs)
        full = candidate if candidate.is_absolute() else (workdir / candidate)
        full = full.resolve()
        try:
            full.relative_to(workdir.resolve())
        except ValueError as exc:
            raise PermissionError(f"路径逃逸沙箱: {rel_or_abs}") from exc
        return full


def _safe_decode(b: bytes) -> str:
    """安全解码 + 长度限制。"""
    if not b:
        return ""
    truncated = b[:_MAX_OUTPUT_BYTES]
    text = truncated.decode("utf-8", errors="replace")
    if len(b) > _MAX_OUTPUT_BYTES:
        text += f"\n... (truncated, original {len(b)} bytes)"
    return text


__all__ = ["LocalProvider"]

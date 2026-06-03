# -*- coding: utf-8 -*-
"""
sandbox_executor.e2b_provider —— E2B 云沙箱 Provider（可配置骨架）

E2B (https://e2b.dev) 是托管的 LLM-friendly 代码执行沙箱：
    - SDK：     e2b / e2b-code-interpreter (Python)
    - 隔离：    每会话一个 Firecracker microVM
    - 网络：    可控（默认开放，可通过 firewall 配置）
    - 文件：    SDK 提供 filesystem.write/read，原生支持文件挂载
    - 流式：    process.stdout / .stderr 是 async iterator

实装策略：
    1. **lazy import**：``e2b`` SDK 是可选依赖；缺失时 ``provision`` 抛
       ``E2BNotAvailable``，由 SkillSandboxRunner 转 FAILED。
    2. **API Key 走 settings/env**：``E2B_API_KEY``；缺失即视为不可用。
    3. **Sandbox.metadata 记录**：
        - sandbox_id（E2B 侧 ID）
        - template_id（镜像）
        - api_key_fingerprint（仅前 8 位，便于审计但不泄露密钥）

⚠️ 当前实装基于 e2b SDK ≥ 0.16 接口约定；如 SDK 改版需更新调用。
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from collections.abc import AsyncIterator
from typing import Any, ClassVar

from loguru import logger

from src.services.sandbox_executor.base import BaseSandboxProvider
from src.services.sandbox_executor.models import (
    ExecResult,
    Sandbox,
    SandboxSpec,
    SandboxStatus,
)


class E2BNotAvailable(RuntimeError):
    """e2b SDK 缺失 或 API Key 未配置。"""


_MAX_OUTPUT_BYTES = 10 * 1024 * 1024


class E2BProvider(BaseSandboxProvider):
    """E2B 云沙箱 Provider。

    Args:
        api_key: 覆盖 ``E2B_API_KEY`` 环境变量
        template: E2B template ID（决定镜像），默认 ``"python3"``
    """

    provider_type: ClassVar[str] = "e2b"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        template: str = "python3",
    ) -> None:
        self.api_key = api_key or os.environ.get("E2B_API_KEY", "")
        self.template = template

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def provision(self, spec: SandboxSpec) -> Sandbox:
        sdk = self._require_sdk()
        if not self.api_key:
            raise E2BNotAvailable("E2B_API_KEY 未配置")

        # E2B SDK 是同步 API；用 to_thread 包成异步
        template = spec.metadata.get("e2b_template") or self.template
        try:
            sbx = await asyncio.to_thread(
                sdk.Sandbox.create,
                template=template,
                api_key=self.api_key,
                metadata={
                    "anxin_skill": spec.metadata.get("skill_name", ""),
                    "anxin_fp": spec.metadata.get("manifest_fingerprint", ""),
                },
            )
        except Exception as exc:
            raise E2BNotAvailable(f"E2B sandbox 创建失败: {exc}") from exc

        sandbox = Sandbox(
            provider_type=self.provider_type,
            status=SandboxStatus.RUNNING,
            spec=spec,
            metadata={
                "sandbox_id": getattr(sbx, "id", None) or getattr(sbx, "sandbox_id", None),
                "template_id": template,
                "api_key_fingerprint": self._fp(self.api_key),
                "_sdk_handle": sbx,  # 保留 SDK 句柄（仅进程内）
            },
        )
        logger.info(f"[E2BProvider] provisioned id={sandbox.metadata['sandbox_id']}")
        return sandbox

    async def terminate(self, sandbox: Sandbox) -> None:
        sbx = sandbox.metadata.get("_sdk_handle")
        if sbx is not None:
            try:
                await asyncio.to_thread(sbx.kill)
            except Exception:
                logger.exception("[E2BProvider] terminate 失败 id=%s", sandbox.metadata.get("sandbox_id"))
        sandbox.status = SandboxStatus.TERMINATED

    # ------------------------------------------------------------------
    # exec
    # ------------------------------------------------------------------

    async def exec(
        self,
        sandbox: Sandbox,
        cmd: list[str],
        stdin: bytes | None = None,
        timeout_sec: int | None = None,
    ) -> ExecResult:
        self._validate_cmd(cmd)
        sbx = sandbox.metadata.get("_sdk_handle")
        if sbx is None:
            raise RuntimeError(f"sandbox={sandbox.id} 未持有 E2B SDK 句柄")

        timeout = timeout_sec if timeout_sec is not None else sandbox.spec.timeout_sec
        start = time.monotonic()
        killed = False

        # E2B SDK 提供 process.run(cmd) 或 commands.run / process.start
        # 这里假定 commands.run 接受 list[str] + timeout
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: sbx.commands.run(
                        " ".join(_shell_quote(a) for a in cmd),
                        timeout=timeout * 1000 if timeout else None,
                    )
                ),
                timeout=timeout + 5,
            )
            stdout = _truncate(getattr(result, "stdout", "") or "")
            stderr = _truncate(getattr(result, "stderr", "") or "")
            exit_code = int(getattr(result, "exit_code", 0) or 0)
        except TimeoutError:
            killed = True
            stdout = ""
            stderr = "E2B exec timeout"
            exit_code = -1
            try:
                # 尝试在 E2B 侧 kill
                await asyncio.to_thread(sbx.kill)
            except Exception:
                pass
        except Exception as exc:
            return ExecResult(
                stdout="",
                stderr=f"E2B exec exception: {exc}",
                exit_code=-1,
                duration_ms=int((time.monotonic() - start) * 1000),
                killed_by_timeout=False,
                cmd=list(cmd),
            )

        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=int((time.monotonic() - start) * 1000),
            killed_by_timeout=killed,
            cmd=list(cmd),
        )

    # ------------------------------------------------------------------
    # 文件 / 日志
    # ------------------------------------------------------------------

    async def upload(self, sandbox: Sandbox, src_path: str, dst_path: str) -> None:
        sbx = sandbox.metadata.get("_sdk_handle")
        if sbx is None:
            raise RuntimeError(f"sandbox={sandbox.id} 未持有 E2B SDK 句柄")
        with open(src_path, "rb") as f:
            data = f.read()
        await asyncio.to_thread(sbx.filesystem.write, dst_path, data)

    async def download(self, sandbox: Sandbox, sandbox_path: str) -> bytes:
        sbx = sandbox.metadata.get("_sdk_handle")
        if sbx is None:
            raise RuntimeError(f"sandbox={sandbox.id} 未持有 E2B SDK 句柄")
        data = await asyncio.to_thread(sbx.filesystem.read, sandbox_path)
        return data if isinstance(data, (bytes, bytearray)) else str(data).encode()

    async def stream_logs(self, sandbox: Sandbox) -> AsyncIterator[str]:
        # E2B 长生命周期场景下可以接 sbx.process.stdout
        # ephemeral exec 模式下 stdout 在 exec 返回时一并拿到 —— 此处仅占位
        if False:  # pragma: no cover
            yield ""
        raise NotImplementedError(
            "E2BProvider.stream_logs：当前为 ephemeral exec 模式，请读 exec 返回值"
        )

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @staticmethod
    def _require_sdk() -> Any:
        try:
            import e2b  # type: ignore[import-not-found]
        except ImportError as exc:
            raise E2BNotAvailable(
                "需要安装 e2b: pip install e2b"
            ) from exc
        return e2b

    @staticmethod
    def _validate_cmd(cmd: list[str]) -> None:
        if not cmd:
            raise ValueError("cmd 不能为空")
        if not isinstance(cmd, list):
            raise TypeError("cmd 必须是 list[str]")
        for a in cmd:
            if not isinstance(a, str):
                raise TypeError(f"cmd 元素必须是 str: {a!r}")
            if "\x00" in a:
                raise ValueError("cmd 含 NUL 字节，拒绝执行")

    @staticmethod
    def _fp(api_key: str) -> str:
        """API Key 指纹（前 8 位 hash），用于审计日志，不泄露密钥本体。"""
        if not api_key:
            return ""
        return "sha256:" + hashlib.sha256(api_key.encode()).hexdigest()[:8]


def _truncate(s: str) -> str:
    b = s.encode("utf-8", errors="replace")
    if len(b) <= _MAX_OUTPUT_BYTES:
        return s
    return b[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")


def _shell_quote(arg: str) -> str:
    """单参数 shell quote —— E2B commands.run 接收 string；用单引号包裹避免注入。"""
    if not arg:
        return "''"
    if all(c.isalnum() or c in "/_.-+=:" for c in arg):
        return arg
    return "'" + arg.replace("'", "'\\''") + "'"


__all__ = ["E2BNotAvailable", "E2BProvider"]

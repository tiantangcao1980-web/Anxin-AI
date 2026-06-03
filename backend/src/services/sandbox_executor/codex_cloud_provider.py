# -*- coding: utf-8 -*-
"""
sandbox_executor.codex_cloud_provider —— Codex Cloud Provider（HTTP 骨架）

形态：远程托管沙箱集群 + REST API 控制，无需本地 SDK。
约定（与设计文档一致，可对接 OpenAI Codex Cloud / 自建 sandbox SaaS）：

    POST   /v1/sandboxes                  -> { sandbox_id, websocket_url }
    POST   /v1/sandboxes/{id}/exec        body: { cmd: [...], stdin?, timeout_ms }
                                          -> { stdout, stderr, exit_code, duration_ms }
    POST   /v1/sandboxes/{id}/files       multipart upload
    GET    /v1/sandboxes/{id}/files?path  -> bytes
    DELETE /v1/sandboxes/{id}             -> {}

依赖：
    - ``httpx`` 已在 backend 依赖中（rag_service 已用）
    - 配置：``CODEX_CLOUD_API_URL`` + ``CODEX_CLOUD_API_KEY``

实装策略：
    - 全部走 HTTP，**不引入新 SDK**
    - 失败时抛 ``CodexCloudUnavailable``；SkillSandboxRunner 自动 FAILED
"""

from __future__ import annotations

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


class CodexCloudUnavailable(RuntimeError):
    """API endpoint 不可达或 API Key 缺失。"""


_MAX_OUTPUT_BYTES = 10 * 1024 * 1024


class CodexCloudProvider(BaseSandboxProvider):
    """远程托管沙箱 Provider。

    Args:
        base_url: 覆盖 ``CODEX_CLOUD_API_URL``
        api_key:  覆盖 ``CODEX_CLOUD_API_KEY``
        timeout:  HTTP 默认超时（秒），默认 30s
    """

    provider_type: ClassVar[str] = "codex_cloud"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("CODEX_CLOUD_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("CODEX_CLOUD_API_KEY", "")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def provision(self, spec: SandboxSpec) -> Sandbox:
        self._require_config()
        client = await self._client()
        try:
            resp = await client.post(
                "/v1/sandboxes",
                json={
                    "image": spec.image,
                    "env_vars": spec.env_vars,
                    "resource_limits": {
                        "cpu_millicores": spec.resource_limits.cpu_millicores,
                        "memory_mb": spec.resource_limits.memory_mb,
                        "disk_mb": spec.resource_limits.disk_mb,
                    },
                    "network": {
                        "mode": spec.network_policy.mode.value,
                        "allowed_hosts": list(spec.network_policy.allowed_hosts),
                    },
                    "metadata": spec.metadata,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            raise CodexCloudUnavailable(f"create sandbox 失败: {exc}") from exc

        sandbox_id = payload.get("sandbox_id")
        if not sandbox_id:
            raise CodexCloudUnavailable("API 返回缺少 sandbox_id")

        sandbox = Sandbox(
            provider_type=self.provider_type,
            status=SandboxStatus.RUNNING,
            spec=spec,
            metadata={
                "sandbox_id": sandbox_id,
                "endpoint": self.base_url,
            },
        )
        logger.info(f"[CodexCloudProvider] provisioned id={sandbox_id}")
        return sandbox

    async def terminate(self, sandbox: Sandbox) -> None:
        sandbox_id = sandbox.metadata.get("sandbox_id")
        if not sandbox_id:
            sandbox.status = SandboxStatus.TERMINATED
            return
        try:
            client = await self._client()
            resp = await client.delete(f"/v1/sandboxes/{sandbox_id}")
            # 404 视为已清理，幂等
            if resp.status_code not in {200, 202, 204, 404}:
                logger.warning(
                    "[CodexCloudProvider] terminate 异常 id=%s status=%s body=%s",
                    sandbox_id, resp.status_code, resp.text[:200],
                )
        except Exception:
            logger.exception("[CodexCloudProvider] terminate 调用失败")
        finally:
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
        sandbox_id = sandbox.metadata.get("sandbox_id")
        if not sandbox_id:
            raise RuntimeError(f"sandbox={sandbox.id} 缺少 sandbox_id")

        timeout = timeout_sec if timeout_sec is not None else sandbox.spec.timeout_sec
        start = time.monotonic()
        client = await self._client()

        import base64 as _b64
        body: dict[str, Any] = {
            "cmd": cmd,
            "timeout_ms": int(timeout * 1000),
        }
        if stdin is not None:
            body["stdin_b64"] = _b64.b64encode(stdin).decode("ascii")

        try:
            resp = await client.post(
                f"/v1/sandboxes/{sandbox_id}/exec",
                json=body,
                timeout=timeout + 10,  # 给服务端处理 +10s buffer
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            return ExecResult(
                stdout="",
                stderr=f"codex_cloud exec exception: {exc}",
                exit_code=-1,
                duration_ms=int((time.monotonic() - start) * 1000),
                killed_by_timeout=False,
                cmd=list(cmd),
            )

        stdout = _truncate(payload.get("stdout") or "")
        stderr = _truncate(payload.get("stderr") or "")
        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=int(payload.get("exit_code", -1)),
            duration_ms=int(payload.get("duration_ms", (time.monotonic() - start) * 1000)),
            killed_by_timeout=bool(payload.get("killed_by_timeout", False)),
            cmd=list(cmd),
        )

    # ------------------------------------------------------------------
    # 文件
    # ------------------------------------------------------------------

    async def upload(self, sandbox: Sandbox, src_path: str, dst_path: str) -> None:
        sandbox_id = sandbox.metadata.get("sandbox_id")
        if not sandbox_id:
            raise RuntimeError(f"sandbox={sandbox.id} 缺少 sandbox_id")
        client = await self._client()
        with open(src_path, "rb") as f:
            content = f.read()
        resp = await client.post(
            f"/v1/sandboxes/{sandbox_id}/files",
            files={"file": (dst_path, content)},
            data={"path": dst_path},
        )
        resp.raise_for_status()

    async def download(self, sandbox: Sandbox, sandbox_path: str) -> bytes:
        sandbox_id = sandbox.metadata.get("sandbox_id")
        if not sandbox_id:
            raise RuntimeError(f"sandbox={sandbox.id} 缺少 sandbox_id")
        client = await self._client()
        resp = await client.get(
            f"/v1/sandboxes/{sandbox_id}/files",
            params={"path": sandbox_path},
        )
        resp.raise_for_status()
        return resp.content

    async def stream_logs(self, sandbox: Sandbox) -> AsyncIterator[str]:
        # WebSocket / SSE 流式 —— 占位
        if False:  # pragma: no cover
            yield ""
        raise NotImplementedError(
            "CodexCloudProvider.stream_logs：用 exec 的 stdout/stderr，或单独连 WS"
        )

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _require_config(self) -> None:
        if not self.base_url:
            raise CodexCloudUnavailable("CODEX_CLOUD_API_URL 未配置")
        if not self.api_key:
            raise CodexCloudUnavailable("CODEX_CLOUD_API_KEY 未配置")

    async def _client(self) -> Any:
        """lazy 构造 httpx.AsyncClient。"""
        try:
            import httpx
        except ImportError as exc:
            raise CodexCloudUnavailable(
                "需要安装 httpx: pip install httpx"
            ) from exc
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "anxin-codex-cloud/1.0",
            },
        )

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


def _truncate(s: str) -> str:
    b = s.encode("utf-8", errors="replace")
    if len(b) <= _MAX_OUTPUT_BYTES:
        return s
    return b[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")


__all__ = ["CodexCloudProvider", "CodexCloudUnavailable"]

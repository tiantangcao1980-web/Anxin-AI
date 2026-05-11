# -*- coding: utf-8 -*-
"""
test_sandbox_local_provider —— LocalProvider 基础用例（P3-E）

覆盖：
    1. provision 创建临时目录并落盘 spec.json
    2. exec 正常返回 stdout / exit_code
    3. exec 超时被强制 kill 并标记 killed_by_timeout
    4. terminate 清理临时目录（且幂等）

仅用 stdlib 工具（echo / sleep / python -c），不依赖任何外部命令。
"""

from __future__ import annotations

import os
import sys

import pytest

from src.services.sandbox_executor import (
    LocalProvider,
    SandboxProviderRegistry,
    SandboxSpec,
    SandboxStatus,
)


pytestmark = pytest.mark.asyncio


@pytest.fixture
def provider() -> LocalProvider:
    return LocalProvider()


async def test_local_provision_creates_dir(provider: LocalProvider) -> None:
    """provision 应当创建临时 workdir 并写入 spec.json。"""
    spec = SandboxSpec(timeout_sec=10, env_vars={"FOO": "bar"})
    sandbox = await provider.provision(spec)
    try:
        assert sandbox.status == SandboxStatus.RUNNING
        assert sandbox.provider_type == "local"
        workdir = sandbox.metadata.get("workdir")
        assert workdir and os.path.isdir(workdir)
        spec_file = sandbox.metadata.get("spec_file")
        assert spec_file and os.path.isfile(spec_file)
        # 验证 sandbox.id 已生成（带 sbx_ 前缀）
        assert sandbox.id.startswith("sbx_")
    finally:
        await provider.terminate(sandbox)


async def test_local_exec_returns_stdout(provider: LocalProvider) -> None:
    """exec 应当返回正确的 stdout 与 exit_code=0。"""
    spec = SandboxSpec(timeout_sec=10)
    sandbox = await provider.provision(spec)
    try:
        # 用当前 Python 解释器跑，避免 PATH 不一致问题
        result = await provider.exec(
            sandbox,
            [sys.executable, "-c", "print('hello-sandbox')"],
        )
        assert result.exit_code == 0
        assert result.killed_by_timeout is False
        assert "hello-sandbox" in result.stdout
        assert result.succeeded is True
        assert result.duration_ms >= 0
        assert result.cmd[-1] == "print('hello-sandbox')"
    finally:
        await provider.terminate(sandbox)


async def test_local_exec_timeout_kills(provider: LocalProvider) -> None:
    """exec 超时应当强制 kill 进程并标记 killed_by_timeout。"""
    spec = SandboxSpec(timeout_sec=10)
    sandbox = await provider.provision(spec)
    try:
        # 让子进程 sleep 5s，但 exec 给 1s 超时
        result = await provider.exec(
            sandbox,
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout_sec=1,
        )
        assert result.killed_by_timeout is True
        # 被 kill 的进程 returncode 通常是负数（信号）或非零
        assert result.exit_code != 0
        assert result.succeeded is False
        # 应当在 ~1s（含收尾）量级，远小于 5s
        assert result.duration_ms < 4500
    finally:
        await provider.terminate(sandbox)


async def test_local_terminate_cleans_dir(provider: LocalProvider) -> None:
    """terminate 应当删除 workdir，且对已终止的沙箱再次调用不报错。"""
    spec = SandboxSpec(timeout_sec=5)
    sandbox = await provider.provision(spec)
    workdir = sandbox.metadata["workdir"]
    assert os.path.isdir(workdir)

    await provider.terminate(sandbox)
    assert not os.path.isdir(workdir)
    assert sandbox.status == SandboxStatus.TERMINATED

    # 幂等：再次调用不应抛异常
    await provider.terminate(sandbox)


# ---------------------------------------------------------------------------
# Registry / 安全防护额外验证（顺手覆盖）
# ---------------------------------------------------------------------------


async def test_registry_default_returns_local() -> None:
    """默认 SANDBOX_PROVIDER=local 时，registry.default() 应返回 LocalProvider。"""
    inst = SandboxProviderRegistry.default()
    assert isinstance(inst, LocalProvider)


async def test_local_exec_rejects_shell_string(provider: LocalProvider) -> None:
    """传入字符串而非 list 应被拒绝（防 shell injection）。"""
    spec = SandboxSpec(timeout_sec=5)
    sandbox = await provider.provision(spec)
    try:
        with pytest.raises(ValueError):
            await provider.exec(sandbox, [])  # 空列表
        with pytest.raises(TypeError):
            # 非 str 元素
            await provider.exec(sandbox, ["echo", 123])  # type: ignore[list-item]
        with pytest.raises(ValueError):
            # 含 NUL 字节
            await provider.exec(sandbox, ["echo", "ok\x00boom"])
    finally:
        await provider.terminate(sandbox)

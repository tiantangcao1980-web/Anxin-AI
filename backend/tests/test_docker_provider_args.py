# -*- coding: utf-8 -*-
"""
DockerProvider.build_docker_args 单测

不依赖 dockerd —— 只验证命令拼装的安全约束：
    - --rm / --user / --cap-drop=ALL / --security-opt no-new-privileges
    - --read-only / --tmpfs /tmp / --pids-limit
    - --memory / --memory-swap（=memory，禁 swap）/ --cpus
    - --network=none 默认；FULL 模式才 bridge
    - workdir 挂载为 /workspace:rw
    - env_vars 通过 -e KEY=VALUE 注入
    - extra mounts 用 :ro 默认

同时验证 _validate_cmd 拒绝非法 cmd。
"""

from __future__ import annotations

import pytest

from src.services.sandbox_executor import (
    DockerProvider,
    NetworkPolicy,
    NetworkPolicyMode,
    ResourceLimits,
    SandboxSpec,
)


def _provider() -> DockerProvider:
    return DockerProvider()


def _spec(**overrides) -> SandboxSpec:
    base = dict(
        image="python:3.11-slim",
        env_vars={"FOO": "bar"},
        resource_limits=ResourceLimits(cpu_millicores=1500, memory_mb=512, disk_mb=2048),
        network_policy=NetworkPolicy(mode=NetworkPolicyMode.NONE),
        timeout_sec=30,
    )
    base.update(overrides)
    return SandboxSpec(**base)


def test_essential_security_flags_present() -> None:
    args = _provider().build_docker_args(
        spec=_spec(),
        workdir="/tmp/wd",
        container_name="anxin-sbx-test",
        cmd=["python", "-c", "print(1)"],
    )
    joined = " ".join(args)

    assert "run" in args
    assert "--rm" in args
    assert "--user" in args and "65534:65534" in args
    assert "--cap-drop=ALL" in args
    # security-opt 是分两个 token：--security-opt no-new-privileges
    assert "no-new-privileges" in args
    assert "--read-only" in args
    assert "--pids-limit" in args and "256" in args
    # tmpfs /tmp 限制大小
    assert any(a.startswith("/tmp:size=") for a in args), joined


def test_memory_and_cpu_propagated() -> None:
    args = _provider().build_docker_args(
        spec=_spec(
            resource_limits=ResourceLimits(
                cpu_millicores=2000, memory_mb=768, disk_mb=1024
            )
        ),
        workdir="/tmp/wd",
        container_name="x",
        cmd=["echo"],
    )
    # 内存与 swap 相等，禁 swap
    assert "768m" in args
    assert args.count("768m") == 2
    # cpus = 2.000
    assert "2.000" in args


def test_network_none_default() -> None:
    args = _provider().build_docker_args(
        spec=_spec(network_policy=NetworkPolicy(mode=NetworkPolicyMode.NONE)),
        workdir="/tmp/wd",
        container_name="x",
        cmd=["echo"],
    )
    assert "none" in args
    # 紧跟 --network
    idx = args.index("--network")
    assert args[idx + 1] == "none"


def test_network_allowlist_falls_back_to_none() -> None:
    """allowlist 暂未实装 iptables，应退化为 none（fail-safe）。"""
    args = _provider().build_docker_args(
        spec=_spec(
            network_policy=NetworkPolicy(
                mode=NetworkPolicyMode.ALLOWLIST,
                allowed_hosts=["api.example.com"],
            )
        ),
        workdir="/tmp/wd",
        container_name="x",
        cmd=["echo"],
    )
    idx = args.index("--network")
    assert args[idx + 1] == "none"


def test_network_full_only_when_explicit() -> None:
    args = _provider().build_docker_args(
        spec=_spec(network_policy=NetworkPolicy(mode=NetworkPolicyMode.FULL)),
        workdir="/tmp/wd",
        container_name="x",
        cmd=["echo"],
    )
    idx = args.index("--network")
    assert args[idx + 1] == "bridge"


def test_workdir_mounted_rw() -> None:
    args = _provider().build_docker_args(
        spec=_spec(),
        workdir="/tmp/anxin-wd",
        container_name="x",
        cmd=["echo"],
    )
    assert "-v" in args
    assert "/tmp/anxin-wd:/workspace:rw" in args
    # -w /workspace
    assert "-w" in args
    idx = args.index("-w")
    assert args[idx + 1] == "/workspace"


def test_env_vars_injected_as_e_pairs() -> None:
    args = _provider().build_docker_args(
        spec=_spec(env_vars={"FOO": "bar", "BAZ": "qux"}),
        workdir="/tmp/wd",
        container_name="x",
        cmd=["echo"],
    )
    # 检查每个 env 都成对出现
    pairs = [
        (args[i], args[i + 1])
        for i, a in enumerate(args[:-1])
        if a == "-e"
    ]
    pair_values = {p[1] for p in pairs}
    assert "FOO=bar" in pair_values
    assert "BAZ=qux" in pair_values


def test_extra_mounts_default_readonly() -> None:
    spec = _spec()
    spec = spec.model_copy(update={"mounts": {"/host/data": "/data"}})
    args = _provider().build_docker_args(
        spec=spec,
        workdir="/tmp/wd",
        container_name="x",
        cmd=["echo"],
    )
    assert "/host/data:/data:ro" in args


def test_cmd_appears_after_image() -> None:
    args = _provider().build_docker_args(
        spec=_spec(image="python:3.12-slim"),
        workdir="/tmp/wd",
        container_name="x",
        cmd=["python", "-c", "print('hi')"],
    )
    assert args[-3:] == ["python", "-c", "print('hi')"]
    # 镜像紧挨在前
    assert args[-4] == "python:3.12-slim"


def test_validate_cmd_rejects_non_list() -> None:
    with pytest.raises(TypeError):
        DockerProvider._validate_cmd("python -c x")  # type: ignore[arg-type]


def test_validate_cmd_rejects_nul() -> None:
    with pytest.raises(ValueError):
        DockerProvider._validate_cmd(["echo", "ok\x00bad"])


def test_validate_cmd_rejects_empty() -> None:
    with pytest.raises(ValueError):
        DockerProvider._validate_cmd([])


def test_container_name_propagated() -> None:
    args = _provider().build_docker_args(
        spec=_spec(),
        workdir="/tmp/wd",
        container_name="anxin-sbx-deadbeef",
        cmd=["echo"],
    )
    idx = args.index("--name")
    assert args[idx + 1] == "anxin-sbx-deadbeef"

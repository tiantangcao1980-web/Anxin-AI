# sandbox_executor —— V3 沙箱执行器（P3-E 骨架）

为 V3 Agent 任务提供统一的**隔离执行**抽象，把"在哪里跑代码"从"跑什么"中解耦。
当前阶段（P3）只交付**骨架 + 唯一可用的 LocalProvider**；DockerProvider /
E2BProvider / CodexCloudProvider 仅占位，真正实装放到 P5/P6。

## 设计目标

| 目标 | 怎么做 |
|------|--------|
| Provider 可插拔 | `BaseSandboxProvider` ABC + `SandboxProviderRegistry` 装饰器注册 |
| 配置驱动切换 | `SANDBOX_PROVIDER` 字段（local/docker/e2b/codex_cloud） |
| 全异步 | `async def` + `AsyncIterator`，匹配 task_orchestrator 的 asyncio worker |
| 安全优先 | 接口禁止 shell 字符串，只接受 `list[str]` argv |
| 状态可序列化 | `Sandbox` / `SandboxSpec` / `ExecResult` 全部 Pydantic v2 |

## 模块结构

```
sandbox_executor/
├── __init__.py            导出公共符号
├── base.py                BaseSandboxProvider（抽象）
├── models.py              SandboxSpec / Sandbox / ExecResult / ResourceLimits / NetworkPolicy
├── registry.py            SandboxProviderRegistry + 内置注册
├── config.py              从 core.config 读 SANDBOX_PROVIDER
├── local_provider.py      ✅ 实装：subprocess 跑命令，仅本地开发/测试
├── docker_provider.py     ⛔ 占位：P5/P6 用 docker-py 实装
├── e2b_provider.py        ⛔ 占位：未来按需接入 E2B SaaS
├── codex_cloud_provider.py⛔ 占位：未来按需接入远程托管沙箱
└── README.md              本文件
```

## 沙箱矩阵

| Provider       | 隔离强度 | 冷启动 | 网络可控 | 资源配额 | 适用场景 | 阶段 |
|----------------|----------|--------|----------|----------|----------|------|
| `local`        | ❌ 无    | ~10ms  | ❌       | ❌       | 单元测试 / 本地 dev | ✅ P3 |
| `docker`       | ✅ 中    | ~1-3s  | ✅       | ✅       | 单机生产 / 自建集群 | ⛔ P5/P6 |
| `e2b`          | ✅ 强    | <300ms | ✅       | ✅       | LLM 生成代码强隔离 | ⛔ 按需 |
| `codex_cloud`  | ✅ 强    | 平台侧 | ✅       | ✅       | 全托管 SaaS         | ⛔ 按需 |

## 接入新 Provider 流程

1. 新建 `xxx_provider.py`，继承 `BaseSandboxProvider`：
   ```python
   class XxxProvider(BaseSandboxProvider):
       provider_type = "xxx"

       async def provision(self, spec): ...
       async def exec(self, sandbox, cmd, stdin=None, timeout_sec=None): ...
       async def upload(self, sandbox, src_path, dst_path): ...
       async def download(self, sandbox, sandbox_path): ...
       def stream_logs(self, sandbox): ...
       async def terminate(self, sandbox): ...
   ```
2. 在 `registry.py` 顶部 import 后调用 `SandboxProviderRegistry.register(XxxProvider)`，
   或直接在自己的模块用装饰器 `@SandboxProviderRegistry.register`。
3. 在 `core/config.py` 的 `SANDBOX_PROVIDER` 字段允许新值（注释里列一下）。
4. 在 `tests/` 下补对应 Provider 的测试。

## 使用示例

```python
from src.services.sandbox_executor import SandboxProviderRegistry, SandboxSpec

provider = SandboxProviderRegistry.default()  # 按 SANDBOX_PROVIDER 取
sandbox = await provider.provision(SandboxSpec(timeout_sec=30))
try:
    result = await provider.exec(sandbox, ["echo", "hello"])
    print(result.stdout, result.exit_code)
finally:
    await provider.terminate(sandbox)
```

## P5 与 task_orchestrator 集成的关键点

当前 `task_orchestrator/worker.py` 直接在 worker 主进程跑业务，没有任何隔离。
P5 阶段的改造点：

1. **provision 时机**：在 `service.start()` 进入 `PROVISIONING` 状态时调用
   `provider.provision(spec)`，spec.mounts 把 task 专属的 git worktree 挂进去。
2. **exec 替换 sleep**：把当前的占位 `asyncio.sleep` 换成 `provider.exec(sbx, ...)`
   实际驱动 agent persona 工具命令。
3. **日志流接入事件总线**：`async for line in provider.stream_logs(sbx)` 直接
   `service.progress(task_id, {"log": line})`。
4. **terminate 兜底**：在 `worker.py` 的 finally 块加 `provider.terminate(sbx)`，
   并在心跳超时检测命中时主动 terminate。
5. **配置切换**：开发用 `SANDBOX_PROVIDER=local`，生产用 `docker` 或 `codex_cloud`。

## 安全注意

- LocalProvider **没有任何隔离**，宿主机用户能做的它全能做。生产请勿启用。
- `exec` 接口强制 `cmd: list[str]`，**禁止** shell=True / shell expansion，
  从源头规避 shell injection（不可拼接 `f"rm {user_input}"` 后传字符串）。
- LocalProvider.upload/download 路径强制解析到沙箱 workdir 内，禁止 `..` 逃逸。
- stdout/stderr 单次抓取上限 10MB，防止 OOM。
- 超时使用 `process.kill()` 强制终结，而非软 SIGTERM 后撒手。

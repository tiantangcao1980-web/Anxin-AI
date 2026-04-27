# skill_executor —— 技能执行器（P5-A 真实装）

## 用途
把 ``skill_registry`` 中加载的 ``Skill`` 当作「可执行单元」运行：
拼 system prompt → 注入 ``ExecutionContext`` → 调 LLM → 返回结构化 ``SkillResult``。

## 模块文件

| 文件 | 角色 |
|------|------|
| `models.py` | `ExecutionContext` / `SkillResult` / `SkillExecutionLog` / `SkillExecutionStatus` |
| `executor.py` | `SkillExecutor`（`execute` / `execute_batch` / `_default_llm_call`） |
| `decorators.py` | `@requires_skill("name")` 给 agent 方法标注依赖 |

## 用法

```python
from src.services.skill_executor import (
    ExecutionContext,
    SkillExecutor,
    requires_skill,
)
from src.services.skill_registry import SkillRegistry

# 加载 + 执行
registry = SkillRegistry.instance()
registry.load_directory("/path/to/skills/")

executor = SkillExecutor(registry=registry)
ctx = ExecutionContext(
    user_id="u1",
    persona="lawyer",
    app_authorizations=["dingtalk", "feishu"],
)
result = await executor.execute("contract-review", {"file": "..."}, ctx)
print(result.ok, result.output)

# 批量执行
batch = await executor.execute_batch(
    [("skill-a", {}), ("skill-b", {"k": "v"})],
    ctx,
    concurrency=4,
)

# Agent 方法依赖标注
class ContractAgent:
    @requires_skill("contract-review")
    async def review(self, text): ...
```

## 与 LLM 的对接

`SkillExecutor.__init__` 接受 `llm_callable: (system, user) -> str | Awaitable[str]`：

- **测试**：直接传 `lambda s, u: "fixed"` 或 `AsyncMock`
- **生产**：默认 `_default_llm_call` 会 lazy-import `services.rag_service._build_llm_client`
  并复用 ``settings.LLM_MODEL``。如果你的 agent 已经有自己的客户端，
  在应用启动时显式注入：

```python
def my_llm(system: str, user: str) -> str:
    return llm_service.complete(system, user)

executor = SkillExecutor(llm_callable=my_llm)
```

## 鉴权语义

| Skill 字段       | ExecutionContext 字段     | 不匹配时的状态        |
|------------------|---------------------------|----------------------|
| `requires_apps`  | `app_authorizations`     | `SKIPPED` + missing  |
| `personas`       | `persona`                 | `SKIPPED`            |
| `enabled=False`  | (n/a)                     | `SKIPPED`            |

## P6+ 扩展
- **tool call**：解析 SKILL.md 中的 `tools:` 段，注册到 LLM `tools` 参数
- **Python sandbox**：cowork docx/pptx 风格 — body 里直接写 Python 让沙箱执行
- **审计落库**：把 `SkillExecutionLog` 写到 `skill_execution_logs` 表

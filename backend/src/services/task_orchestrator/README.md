# task_orchestrator —— 异步任务编排（P1 骨架）

## 用途
参考 **Codex Cloud / Claude Dispatch** 模式：用户在 App 派发任务，agent 在远端 sandbox 中执行，完成后回报。前端可通过 SSE 订阅 `task.*` 事件，看到从入队到完成的完整生命周期。

与既有 `models/task.py`（用户/案件待办的 `tasks` 表）**互不影响**：本模块使用独立的 `agent_tasks` 表。

## 状态机

```
queued ──► provisioning ──► running ──► reporting ──► done
                              │           │
                              │           └──► needs_approval ──► running
                              │                                   │
                              └─────────────► failed ◄────────────┘
```

终态：`done` / `failed`。
所有转移必须经 `TaskStateMachine.transition(...)`，自动写入 `started_at` / `finished_at` 并发出 `TaskEvent`。

## 文件结构

| 文件 | 角色 |
|------|------|
| `models.py` | `Task` ORM（表 `agent_tasks`）+ `TaskStatus` |
| `state_machine.py` | `TaskStateMachine`、`TRANSITIONS`、`InvalidTransitionError` |
| `events.py` | `TaskEvent` / `TaskEventType` DTO |
| `service.py` | `TaskOrchestratorService` 服务门面（P2 实现） |

## P2 实现路线

1. **alembic 迁移**：`alembic revision --autogenerate -m "create agent_tasks"`，审阅生成的 enum / 索引。
2. **执行总线**：`enqueue` 接 Redis Stream（推荐 `XADD agent_tasks_stream`），worker 用消费组接收。
3. **Sandbox 接入**：先实现自建 runner（Docker Sandbox），后续抽象 `SandboxProvider`，支持 Codex Cloud。
4. **事件总线**：`TaskStateMachine` 的 `emitter` 注入 Redis Pub/Sub Publisher，前端 SSE 网关订阅 `task:{user_id}` 频道。
5. **审批流**：`request_approval` 与 `models/approval.py` 联动，指派人审批后回到 `running`。
6. **超时与重试**：worker 心跳 + 状态机超时检测（30 分钟无心跳自动 `failed`）。

## P3+ 扩展
- 任务依赖图（DAG）：基于 `parent_task_id` 拓展为多父依赖；
- 多租户配额：按 `user_id` + `agent_persona` 限流；
- 审计 / 复盘：归档已完成任务到冷库，配合 `services/audit_service.py`。

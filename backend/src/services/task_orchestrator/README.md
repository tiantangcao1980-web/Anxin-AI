# task_orchestrator —— 异步任务编排（P2 MVP 已实装）

## 用途
参考 **Codex Cloud / Claude Dispatch** 模式：用户在 App 派发任务，agent 在远端 sandbox 中执行，完成后回报。前端可通过 SSE 订阅 `task.*` 事件，看到从入队到完成的完整生命周期。

与既有 `models/task.py`（用户/案件待办的 `tasks` 表）**互不影响**：本模块使用独立的 `agent_tasks` 表。

## 状态机

```
queued ──► provisioning ──► running ──► reporting ──► done
            │                 │           │
            │                 │           └──► needs_approval ──► running
            │                 │                                   │
            └─► cancelled ◄───┴───── failed ◄────────────────────┘
```

终态：`done` / `failed` / `cancelled`。
所有转移必须经 `TaskStateMachine.transition(...)`，自动写入 `started_at` / `finished_at` 并发出 `TaskEvent`。

## 文件结构

| 文件 | 角色 |
|------|------|
| `models.py` | `Task` ORM（表 `agent_tasks`）+ `TaskStatus` |
| `state_machine.py` | `TaskStateMachine`、`TRANSITIONS`、`InvalidTransitionError` |
| `events.py` | `TaskEvent` / `TaskEventType` + Redis Streams 持久化（publish/replay/consume） |
| `service.py` | `TaskOrchestratorService` 服务门面（已实装） |
| `celery_app.py` | Celery 实例（broker/backend = Redis） |
| `worker.py` | `run_agent_task` Celery 任务 — P2 占位 |

## 已实装（P2 MVP）

1. **状态机扩展**：新增 `cancelled` 终态，覆盖用户主动取消 + 审批驳回。
2. **TaskOrchestratorService 全方法**：
   `create_task / enqueue / start / progress / complete / fail / request_approval / approve / reject / cancel / get_task / list_tasks_for_user`。
3. **Celery worker（占位）**：`worker.run_agent_task(task_id)` — 执行 `start → 模拟 progress×3 → complete`，验证状态流转 + 事件流通。
4. **事件总线**：Redis Streams（key `agent_task_events:{task_id}`），SSE 端点用 `consume_events()` 阻塞读 + Last-Event-ID 续传。
5. **Alembic 迁移** `028_add_agent_tasks_table.py`：含 enum、索引（user_id/status/priority/created_at），可逆。
6. **API 端点** `/api/v1/agent-tasks/...`：8 个端点，跨用户访问拦截，super_admin / admin 放行。
7. **测试**：state machine（参数化合法/非法转移）+ service（生命周期）+ API（SSE 除外，HTTP 端点完整覆盖）。

> 测试运行说明：测试文件已 monkeypatch `publish_event` / `enqueue` 为 no-op，**无需** Redis / Celery 进程即可跑通。如需真实端到端验证，请在本地 docker-compose 启动 Redis 后启动 worker：
> ```
> celery -A src.services.task_orchestrator.celery_app:celery_app worker -l info -Q agent_tasks
> ```

## 占位项（待后续阶段实装）

- **P3**：沙箱隔离（Docker Sandbox / Codex Cloud）、心跳超时检测、推送通知 / IM 转发。
- **P5**：worker 内真正调度 agent persona（当前只是 sleep + 占位 result）。
- **P3+**：审批流接 `models/approval.py` 联动通知；任务 DAG（多父依赖）。

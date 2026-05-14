# TASK-11b Sync Engine — PRD Reality Gap

> 日期：2026-05-06
> 范围：桌面同步引擎从骨架走向真实跨端同步。

## PRD 承诺

- 桌面端离线任务队列可持久化。
- 桌面端能 push 本地变更到云端。
- 桌面端能 pull 云端增量并写回本地。
- 桌面开始的会话可被移动端继续。
- 绝密模式不上行，混合/云端模式按策略同步。

## 代码现实

- `desktop/migrations/001_offline_queue.sql` 已有本地消息、文档、案件、合同、`sync_log`、`offline_tasks`、`local_artifacts` 表的初始化 SQL，并通过 Rust-owned SQLCipher service 应用到 `sqlcipher:anxin_local.db`。
- `desktop/src/services/sync_engine.rs` 已补 Rust IPC fallback 与 packaged-binary smoke：可读取 retryable `sync_log` 行、构造 push payload、处理 accepted/conflict/failed、写回 pull 记录与 cursor，并通过 `--sync-loopback-smoke` 在 unsigned release `.app` 二进制内启动本地 HTTP loopback 后端，验证 bearer-auth push/pull/conflict/retry 流程。
- `frontend/src/lib/api-adapter.ts` 已通过 Rust secure SQL commands 接入真实本地 SQLCipher 同步路径：读取 `sync_log`、push 到后端、pull 后写回本地业务表并推进 `sync.last_server_version`。
- `desktop/src/commands/sync.rs` 已停止用空 payload 打后端并误报成功；Rust IPC fallback 已具备 SQLCipher pending/failed push、accepted/conflict/failed 写回、pull 本地表写回和 cursor 更新的代码级路径，前端 bridge 仍是桌面交互入口。
- 后端 `/api/v1/sync/*` 已存在；本轮前 `SyncService` 只是进程内内存字典。
- 本轮已补后端 `sync_log` 数据库模型、Alembic 迁移和 DB-backed `SyncService`，后端 push/pull/user isolation 具备耐久落点。

## 差距结论

后端同步日志从“重启丢失”推进为“数据库耐久增量日志”；桌面 Rust SQLCipher 路径已完成最小 push/pull/writeback，失败记录已有 retry/backoff 与 `needs_human` 标记，冲突处理已有 `/sync-conflicts` 专用页面和 merge 草稿编辑，SQLCipher/keyring 本地 installed-profile smoke、unsigned release packaged-profile smoke、100/500 本地性能基线和 unsigned release packaged-binary loopback push/pull/conflict/retry transcript 已通过；但仍缺 signed/notarized installer 与 signed packaged-profile migration、signed packaged runtime performance、真实交互式 Tauri UI conflict/human-intervention transcript、共享预发后端 sync transcript 和跨端连续会话验证。本任务仍不可标商业完成。

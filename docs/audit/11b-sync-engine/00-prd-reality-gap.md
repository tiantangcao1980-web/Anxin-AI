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
- `desktop/src/services/sync_engine.rs` 仍未读取 SQLite，`push_pending_records` / `pull_incremental_updates` 仍是占位。
- `frontend/src/lib/api-adapter.ts` 已通过 Rust secure SQL commands 接入真实本地 SQLCipher 同步路径：读取 `sync_log`、push 到后端、pull 后写回本地业务表并推进 `sync.last_server_version`。
- `desktop/src/commands/sync.rs` 已停止用空 payload 打后端并误报成功；Rust 侧已拥有本地 SQLCipher 读写命令，但端到端同步编排仍在前端 bridge。
- 后端 `/api/v1/sync/*` 已存在；本轮前 `SyncService` 只是进程内内存字典。
- 本轮已补后端 `sync_log` 数据库模型、Alembic 迁移和 DB-backed `SyncService`，后端 push/pull/user isolation 具备耐久落点。

## 差距结论

后端同步日志从“重启丢失”推进为“数据库耐久增量日志”；桌面 Rust SQLCipher 路径已完成最小 push/pull/writeback，失败记录已有代码级 retry/backoff 与 `needs_human` 标记，冲突处理已有 `/sync-conflicts` 专用页面和 merge 草稿编辑，SQLCipher/keyring 本地 installed-profile smoke 和 100/500 本地性能基线已通过；但仍缺真实 Tauri packaged UI smoke、retry/backoff packaged runtime 证据、signed/notarized packaged-profile migration、packaged runtime 性能和移动端连续会话验证。本任务仍不可标商业完成。

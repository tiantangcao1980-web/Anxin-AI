# TASK-11b 桌面同步引擎（实质从零实现）

> 波次 4 · 工时估 7-10 天（实质从零）
> 前置依赖：任务 0（密钥治理 SOP）、任务 1（认证 + token 存储确定 → 同步接口要 Bearer Token）、任务 6（对象存储抽象层 → 文件 records 落地）
> 下游依赖：任务 11a（拖拽分析的文件需要同步管道）、任务 11c（移动端跨设备会话延续 = ROADMAP M3 直接依赖本任务）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`../00-platform/03-cross-cutting-gaps.md` §1 缺口 C（**本任务的全部背景**）、`PRODUCT_ROADMAP.md` M3 跨设备会话延续

---

## 1. 范围

### 基础事实（不可绕过）

- 当前 `desktop/src/commands/sync.rs` 第 18 行的 `build_push_body` push 体永远是空数组
- 当前 `desktop/src/commands/sync.rs` 第 99 行 pull 拿到响应直接丢弃
- 当前 `desktop/src/services/sync_engine.rs` 第 91 行 `push_pending_records` 仅 log + `Ok(0)`
- 当前 `desktop/src/services/sync_engine.rs` 第 102 行 `pull_incremental_updates` 同上 `Ok(0)`
- **HTTP 链路通了，但 SQLite 离线队列从未被读写**
- **本任务实质是从零写**，不是"修补"。工时按 7-10 天计

### 要碰的文件

- 桌面 Rust：
  - `desktop/src/services/sync_engine.rs`（整体重写 push / pull / 冲突合并 / 重试）
  - `desktop/src/commands/sync.rs`（重写 `build_push_body` 与 pull 写回）
  - **新建** `desktop/migrations/001_offline_queue.sql`（SQLite schema）
  - **新建** `desktop/src/models/sync.rs`（OfflineTask / SyncState / ConflictRecord 数据模型）
  - 已有 `desktop/src/commands/sync.rs:155 resolve_conflict`（保留接口，重写实现）
- 后端：
  - `backend/src/services/sync_service.py`（适配 device_id + user_id 隔离 + version 增量）
  - `backend/src/api/routes/sync.py`（push / pull 路由实现）
  - **新建** alembic 迁移：`sync_log` 表（记录所有变更供 pull 增量回放）
- 测试：
  - **新建** `desktop/tests/sync_push.rs`
  - **新建** `desktop/tests/sync_pull.rs`
  - **新建** `desktop/tests/sync_conflict.rs`
  - **新建** `backend/tests/test_sync_push.py`
  - **新建** `backend/tests/test_sync_pull.py`
  - **新建** `backend/tests/test_sync_isolation.py`（device_id + user_id 隔离）

### 不要碰的文件

- `desktop/tauri.conf.json` / `desktop/src/main.rs` 窗口部分（任务 11a）
- `desktop/src/commands/global_shortcut.rs` / `tray.rs`（任务 11a）
- `frontend/src/lib/design-tokens.ts`
- `backend/src/services/object_storage_service.py`（任务 6 已交付，本任务只调用）
- `backend/src/prompts/`
- payment / billing / subscription 任意文件
- 任何 secret / `.env`

---

## 2. 必修 P0（带文件:行号 + 期望状态）

| # | 文件 | 现状 | 期望 |
|---|---|---|---|
| P0-1 | 新建 `desktop/migrations/001_offline_queue.sql` | 缺 | `offline_tasks`（id PK / entity_type / entity_id / operation / payload BLOB / created_at / status pending\|syncing\|synced\|failed / retry_count / last_error）+ `sync_state`（key PK / value）+ 索引 status / (entity_type, entity_id) |
| P0-2 | `desktop/src/services/sync_engine.rs:91` 重写 `push_pending_records` | `Ok(0)` 占位 | 读 `WHERE status='pending'` 限 100 条 → POST `/api/v1/sync/push` → 按 `{accepted, rejected}` 标 synced / failed + last_error |
| P0-2 | `desktop/src/commands/sync.rs:18` 重写 `build_push_body` | 永远空数组 | 从 SQLite 读 pending 任务序列化为 push body |
| P0-3 | `desktop/src/services/sync_engine.rs:102` 重写 `pull_incremental_updates` | `Ok(0)` 占位 | GET `/api/v1/sync/pull?since_version=X` → 按 entity_type 写入本地 SQLite 各业务表 → 更新 `sync_state['last_sync_version']` |
| P0-3 | `desktop/src/commands/sync.rs:99` 去掉响应丢弃 | `let _ = r.json()` | 真正解析响应 + 调 sync_engine 写回 |
| P0-4 | `frontend/src/pages/SyncConflicts.tsx` + `frontend/src/lib/api-adapter.ts` | ✅ 代码级已补；runtime 未验 | conflict 行持久化到 `sync_log.status='conflict'`；前端 `/sync-conflicts` 展示本地/云端 JSON、提供 keep-local/keep-remote/merge；仍需 packaged Tauri runtime smoke |
| P0-5 | `backend/src/services/sync_service.py` + `backend/src/api/routes/sync.py` | sync 接口未实现 device_id 隔离 + version 增量 | push: 校验 user 拥有 entity；按 entity_type 路由到对应 service upsert；写 sync_log（含 device_id 来源）。pull: 基于 sync_log `WHERE user_id=? AND version > ?` 增量返回；同 user 不同 device 互通，跨 user 完全隔离 |
| P0-6 | `frontend/src/lib/api-adapter.ts` retry scheduler | ✅ 代码级已补；runtime 未验 | 失败 push 行写入 `retry_count` / `next_retry_at` / `needs_human`，按有界指数退避排队；仍需 packaged Tauri runtime smoke 证明 |
| P0-7 | `desktop/src/services/sync_engine.rs` SQLite 加密 | 本地 SQLite 明文 | 接 `sqlcipher`（或 `tauri-plugin-sql` + sqlcipher feature）；密钥从系统 keyring 读（macOS Keychain / Windows DPAPI）；首次启动生成；绝密模式数据强制加密 |

---

## 3. 流程（Step 0-7）

### Step 0 · PRD vs 代码差分（强制）

产出 `docs/audit/11b-sync-engine/00-prd-reality-gap.md`：
- PROJECT_STATUS / ROADMAP 自宣"离线任务队列 + 同步引擎已完成" vs 代码 4 处 `Ok(0)` / 空数组的真实状态
- 列横切缺口 C（本任务自身）
- 列任务 11a 拖拽落地、任务 11c 跨设备会话延续对本任务的依赖
- 列后端 sync_service 当前状态（是否已有 sync_log 表；是否已有 device_id 字段；是否已有 user_id 隔离查询）

### Step 1 · 检索复用

- `/hierarchical-memory find-feature "SQLite 离线队列 push pull 同步"`
- `/hierarchical-memory find-feature "last-writer-wins 冲突合并"`
- `/hierarchical-memory find-feature "tauri-plugin-sql migration sqlcipher"`
- `/iterative-retrieval` 按 `migrations → models/sync.rs → services/sync_engine.rs → commands/sync.rs → 后端 sync 路由 → 后端 sync_log 表 → 测试` 分层读

### Step 2 · P0-1 schema + migration

1. 新建 `desktop/migrations/001_offline_queue.sql` 落地 `offline_tasks` + `sync_state` + `conflicts`
2. 走 `tauri-plugin-sql` migration 注册（**不允许手动改 schema**）
3. 后端 alembic：新增 `sync_log` 表（id / user_id / device_id / entity_type / entity_id / operation / payload / version BIGINT / created_at），版本号用 sequence
4. 本地 + Postgres 双跑 upgrade / downgrade

### Step 3 · P0-2 push（SQLite → 云端）

1. 新建 `desktop/src/models/sync.rs` 定义 `OfflineTask` 结构体 + `from_row` / `to_push_record`
2. 重写 `commands/sync.rs:18 build_push_body`：从 SQLite 读 `status='pending' LIMIT 100`，按时序排序
3. 重写 `services/sync_engine.rs:91 push_pending_records`：调 `build_push_body` → POST → 解析 `{accepted: [id...], rejected: [{id, reason}]}` → 批量更新本地状态
4. 后端 `routes/sync.py` push 路由：校验 Bearer Token → 校验每条 record 的 entity 归属 user → 路由到对应 service upsert → 写 `sync_log` → 返回结果
5. 单测：mock SQLite + mock HTTP，覆盖 全部 accepted / 全部 rejected / 部分 accepted 三种路径

### Step 4 · P0-3 pull（云端 → SQLite）

1. 重写 `services/sync_engine.rs:102 pull_incremental_updates`：从 `sync_state` 读 `last_sync_version` 作为 `since_version`，GET `/api/v1/sync/pull?since_version=X&limit=500`
2. 后端 `routes/sync.py` pull 路由：`SELECT * FROM sync_log WHERE user_id = ? AND version > ? ORDER BY version LIMIT 500`
3. 桌面端把响应按 entity_type 路由写入对应本地表（cases / contracts / documents / messages / ...）
4. 写完后 `sync_state['last_sync_version'] = max(version)`
5. 重写 `commands/sync.rs:99` 不再丢弃响应
6. 单测：覆盖 空响应 / 单 entity / 多 entity 混合 / 跨 user 不返回别人数据 三种路径

### Step 5 · P0-4 冲突合并

1. 新建 `desktop/src/services/conflict_resolver.rs`
2. pull 写回时检查 `local.updated_at` vs `remote.updated_at`：
   - remote 更新 → 直接覆盖（last-writer-wins 默认）
   - local 更新且与 remote 冲突 → 写入 `conflicts` 表（包含 local_payload + remote_payload + entity_type + entity_id），前端展示
3. 复用 `commands/sync.rs:155 resolve_conflict` 上行接口让用户手动选择
4. 单测：覆盖 仅本地改 / 仅云端改 / 双方都改时间戳同 / 双方都改本地新 / 双方都改云端新 五种路径

### Step 6 · P0-5 后端隔离 + P0-6 自动重试 + P0-7 加密

1. 后端：sync_service push / pull 全部加 `user_id` 过滤（fail-closed，未传 user_id 直接 401）
2. 后端：限流按 `device_id + user_id` 维度（防恶意刷），用现有 Redis 限流中间件
3. 桌面：新建 tokio background task `retry_failed_tasks`：每 60s 扫描 + 指数退避；超 24h 标 `needs_human`
4. 桌面：SQLite 接 sqlcipher，密钥经 keyring；绝密模式强制加密；非绝密模式可选

### Step 7 · 验证 + 沉淀

- `/verification-loop`：
  - 桌面：`cargo check` + `cargo clippy` + `cargo test`（新增至少 15 个用例：push 3 + pull 3 + conflict 5 + retry 2 + isolation 2）
  - 后端：`pytest`（新增至少 10 个用例覆盖 push / pull / 隔离 / 限流）
  - 全栈：273 baseline 后端测试不退化
- 性能基线：100 条 records push P95 < 2s；500 条 pull P95 < 3s
- `/security-review`：重点查 sqlcipher 密钥存储路径 + sync 接口越权
- `add-feature --name "desktop-sync-engine" --pattern "SQLite 离线队列 + push/pull + last-writer-wins 冲突合并 + sqlcipher 加密" --files ...`
- 更新 `PRODUCT_ROADMAP.md`：把 M3 跨设备会话延续 从 "已完成（骨架）" 改为 "前置依赖已交付，待 50 用户灰度 14 天"
- 更新 `PROJECT_STATUS.md`：移除横切缺口 C 钉子

---

## 4. 输出物

```
docs/audit/11b-sync-engine/
├─ 00-prd-reality-gap.md
├─ 01-prd-coverage.md
├─ 02-issues.md
├─ 03-fixes.md
├─ 04-test-additions.md
└─ 05-followups.md
```

附加：
- `docs/desktop/sync-engine-design.md`（schema + push/pull 协议 + 冲突合并 + 重试 + 加密五件套设计）
- `docs/desktop/sync-engine-protocol.md`（前后端接口契约：push body / pull response / 错误码）
- `docs/desktop/sync-engine-runbook.md`（运维手册：怎么看 conflicts 表、怎么处理 needs_human、怎么重置 last_sync_version）

---

## 5. 风险护栏

- **SQLite schema 改动**：必须走 `tauri-plugin-sql` migration 机制；不允许手动 ALTER TABLE；每条 migration 给回滚 SQL
- **灰度**：上线前 50 个种子用户灰度跑至少 14 天，监控指标：push 成功率 / pull 延迟 / 冲突触发率 / needs_human 数量
- **隔离限流**：后端 sync 接口必须按 `device_id + user_id` 维度限流（默认 60 req/min），防恶意刷；fail-closed
- **加密密钥**：sqlcipher 密钥不允许写到任何 log / error message / 文件；只在 keyring 中；首次启动失败要给明确错误而非 fallback 明文
- **本任务是 ROADMAP M3 前置**："跨设备会话延续（桌面开始 → 手机继续）"完全依赖本任务，未交付前移动端任务 11c 不得 mock 本同步链路
- **本任务是任务 11a 的运行时基础**：任务 11a P0-3 拖拽分析落地的文件依赖本同步队列，未交付前任务 11a 的拖拽只能"入队但不上行"
- **不动**：sync 协议字段不允许擅自改名（要兼容已上线设备）；冲突合并默认策略要先 PR 评审后才能切换为非 last-writer-wins
- **绝密模式**：本同步在绝密模式下默认完全不上行，仅本地 SQLite；混合模式按隐私层级过滤；云端模式全量；任何模式切换必须用户主动确认
- **不动**：design-tokens / payment / prompts / 任务 11a 的窗口外观文件
- **测试 fixture**：禁止用真实生产数据，全部用 factory + faker

---

## 6. 完成标准（DoD）

- [ ] `desktop/migrations/001_offline_queue.sql` 落地，`tauri-plugin-sql` migration 上行 / 回滚双向跑通
- [ ] `offline_tasks` + `sync_state` + `conflicts` 三张表 schema 与 `docs/desktop/sync-engine-design.md` 完全对齐
- [ ] push 实测：本地 SQLite 写 100 条 pending → 单次 push → 云端 sync_log 落地 100 条 + 本地 100 条标 synced；时间 < 2s
- [ ] pull 实测：从 0 同步 500 条增量 → 本地 5 张业务表正确写入 + `last_sync_version` 推进；时间 < 3s
- [ ] 冲突合并 runtime：代码级 `/sync-conflicts` 和 merge JSON 校验已补；仍需真实 Tauri runtime 验证列表、保留本地、保留云端、提交合并
- [ ] 自动重试 runtime：代码级退避与 `needs_human` 已补；仍需在真实 Tauri runtime 中验证失败、延迟重试、达到上限转人工处理
- [ ] sqlcipher 接通：本地 SQLite 文件用 hex 工具打开看不到明文；密钥在 macOS Keychain / Windows Credential Manager 可查
- [ ] 后端 sync 接口：跨 user 完全隔离（A 用户 pull 永远拿不到 B 用户的 sync_log）；按 device_id + user_id 限流生效
- [ ] 桌面 `cargo test` 新增至少 15 个用例全绿；后端 `pytest` 新增至少 10 个用例全绿；全栈 273 baseline 不退化
- [ ] 性能基线达标：push 100 条 P95 < 2s；pull 500 条 P95 < 3s
- [ ] `docs/audit/11b-sync-engine/01..05.md` + `docs/desktop/sync-engine-{design,protocol,runbook}.md` 全部产出
- [ ] 经验沉淀到 hierarchical-memory（add-feature ≥ 1 + add-bugfix ≥ 1）
- [ ] `PROJECT_STATUS.md` 横切缺口 C 标记移除；`PRODUCT_ROADMAP.md` M3 状态更新

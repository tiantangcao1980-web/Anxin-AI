# TASK-11b 桌面同步引擎（实质从零实现）
> ⚠️ **2026-05-20 路线纠正**：本文档涉及的 uni-app / apps/uni-mobile 技术链路已**彻底放弃**。
> 当前移动端路线 = mobile/ (Expo + RN) + mini-program/ (Taro)，详见 PROJECT_STATUS.md 和 PRODUCT_ROADMAP.md。
> 以下内容保留为历史决策上下文，不代表当前实施方向。

> 波次 4 · 工时估 7-10 天（实质从零）
> 前置依赖：任务 0（密钥治理 SOP）、任务 1（认证 + token 存储确定 → 同步接口要 Bearer Token）、任务 6（对象存储抽象层 → 文件 records 落地）
> 下游依赖：任务 11a（拖拽分析的文件需要同步管道）、任务 11c（移动端跨设备会话延续 = ROADMAP M3 直接依赖本任务）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`../00-platform/03-cross-cutting-gaps.md` §1 缺口 C（**本任务的全部背景**）、`PRODUCT_ROADMAP.md` M3 跨设备会话延续

> 2026-05-08 定位补充：同步引擎不只同步业务数据，还要成为桌面主工作站与移动随身助手之间的会话连续、远程命令、审批确认和执行状态回传底座。绝密/本地模式下默认不上行，移动远控也必须遵守用户授权和隐私模式。

---

## 1. 范围

### 基础事实（不可绕过）

- 2026-05-08 后旧 Rust IPC 假成功已清除：未启用时返回 unsupported/fail-closed，并报告本地待同步、离线任务和冲突统计
- 2026-05-09 增量：`desktop/src/commands/sync.rs` 的 Rust IPC fallback 已接入真实 SQLCipher `sync_log` 数据面，可读 pending/failed 行、POST `/api/v1/sync/push`、按 accepted/conflict/failed 写回、GET `/api/v1/sync/pull` 并按 entity_type 写入本地业务表；当前证据为代码级 `cargo test sync`，仍缺真实 backend + packaged runtime push/pull/conflict/retry 交互证据
- 2026-05-09 增量：桌面二进制新增 `--sync-code-smoke`，并接入 `scripts/desktop-release-runtime-smoke.sh`；真实 `.app` 二进制可验证同步迁移、pending/deferred/conflict/needs_human 计数、push payload、冲突 accepted 行选择、retry needs_human 和 pull response 解码。该证据仍是 packaged-binary supporting smoke，不替代真实 backend + packaged runtime push/pull/conflict/retry 交互证据
- `desktop/src/services/sync_engine.rs` 的后台 `SyncEngine::push_pending_records` / `pull_incremental_updates` 仍保持未启用时返回 Error，不再 `Ok(0)`；后台常驻同步循环需后续把 AppHandle/SQLCipher 数据面纳入服务层
- 前端 `frontend/src/lib/api-adapter.ts` 已承担 SQLCipher 本地同步路径；仍缺 signed packaged runtime 证据证明真实环境可 push/pull/retry/conflict
- **本任务现在不是修补假成功，而是补真实云端数据面、跨设备会话延续、移动远控命令队列和商业证据**。工时仍按 7-10 天计

### 要碰的文件

- 桌面 Rust：
  - `desktop/src/services/sync_engine.rs`（整体重写 push / pull / 冲突合并 / 重试）
  - `desktop/src/commands/sync.rs`（若启用 Rust IPC 数据面，接入真实 pending-record 序列化与 pull 写回；未启用时继续 fail-closed）
  - **新建** `desktop/migrations/001_offline_queue.sql`（SQLite schema）
  - **新建** `desktop/src/models/sync.rs`（OfflineTask / SyncState / ConflictRecord 数据模型）
  - 已有 `desktop/src/commands/sync.rs:155 resolve_conflict`（保留接口，重写实现）
  - **新建/预留** `desktop/src/models/remote_command.rs`（RemoteCommand / DevicePairing / RemoteCommandAudit 数据模型）
  - **新建/预留** `desktop/src/services/remote_command_queue.rs`（移动远控命令入队、确认、取消、状态回传）
- 后端：
  - `backend/src/services/sync_service.py`（适配 device_id + user_id 隔离 + version 增量）
  - `backend/src/api/routes/sync.py`（push / pull 路由实现）
  - **新建/预留** `backend/src/api/routes/device_pairing.py` 或同步路由子路径（设备配对、撤销和远控审计）
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
| P0-2 | `desktop/src/services/sync_engine.rs:191` 数据面 push | 已 fail-closed，不再 `Ok(0)`；真实云端 push 未启用 | 读真实本地待同步记录 → POST `/api/v1/sync/push` → 按 `{accepted, rejected}` 标 synced / failed + last_error，或继续保持明确 unsupported |
| P0-2 | `desktop/src/commands/sync.rs` 直连同步 IPC | ✅ 代码级已启用 fallback 数据面：读取 SQLite pending/failed 行、补 `sync.device_id`、构造真实 push body，不包含本地 `sync_log.id` | 还需 packaged Tauri runtime + 真实/预发 backend 证明 100 条 pending push 后云端 `sync_log` 和本地状态一致 |
| P0-3 | `desktop/src/services/sync_engine.rs:199` 数据面 pull | 已 fail-closed，不再 `Ok(0)`；真实云端 pull 未启用 | GET `/api/v1/sync/pull?since_version=X` → 按 entity_type 写入本地 SQLite 各业务表 → 更新 `sync_state['last_sync_version']`，或继续保持明确 unsupported |
| P0-3 | `desktop/src/commands/sync.rs` pull 写回 | ✅ 代码级已启用 fallback pull 写回：解析 `/sync/pull` records，支持 message/document/conversation/case/contract/setting/harness artifact/delete，并更新 `sync.last_server_version` / `sync.last_sync_time` | 还需 packaged runtime 证明 pull 写回、冲突页、退避重试和人工处理状态在真实 UI 中可见 |
| P0-4 | `frontend/src/pages/SyncConflicts.tsx` + `frontend/src/lib/api-adapter.ts` | ✅ 代码级已补；runtime 未验 | conflict 行持久化到 `sync_log.status='conflict'`；前端 `/sync-conflicts` 展示本地/云端 JSON、提供 keep-local/keep-remote/merge；仍需 packaged Tauri runtime smoke |
| P0-5 | `backend/src/services/sync_service.py` + `backend/src/api/routes/sync.py` | sync 接口未实现 device_id 隔离 + version 增量 | push: 校验 user 拥有 entity；按 entity_type 路由到对应 service upsert；写 sync_log（含 device_id 来源）。pull: 基于 sync_log `WHERE user_id=? AND version > ?` 增量返回；同 user 不同 device 互通，跨 user 完全隔离 |
| P0-6 | `frontend/src/lib/api-adapter.ts` retry scheduler | ✅ 代码级已补；runtime 未验 | 失败 push 行写入 `retry_count` / `next_retry_at` / `needs_human`，按有界指数退避排队；仍需 packaged Tauri runtime smoke 证明 |
| P0-7 | `desktop/src/services/sync_engine.rs` SQLite 加密 | 本地 SQLite 明文 | 接 `sqlcipher`（或 `tauri-plugin-sql` + sqlcipher feature）；密钥从系统 keyring 读（macOS Keychain / Windows DPAPI）；首次启动生成；绝密模式数据强制加密 |
| P0-8 | 远程命令队列 + 设备配对 + 审计 | 后端同步路由已补 `/sync/remote-control/status`、`pairings`、`commands` fail-closed 契约：未配置、绝密/本地模式、缺二次确认、缺配对、缺 route token、缺队列/审计均拒绝且不入队；真实设备配对、桌面 host、队列、状态回传和审计仍未实现 | 支持 mobile -> desktop 的 command queue：pairing、permission scope、pending/accepted/running/succeeded/failed/cancelled 状态、敏感动作确认、撤销、过期、审计日志；绝密模式默认拒绝外部命令，除非用户在桌面端显式授权 |

---

## 3. 流程（Step 0-7）

### Step 0 · PRD vs 代码差分（强制）

产出 `docs/audit/11b-sync-engine/00-prd-reality-gap.md`：
- PROJECT_STATUS / ROADMAP 自宣"离线任务队列 + 同步引擎已完成" vs 当前 fail-closed Rust IPC、前端 SQLCipher 同步路径、packaged runtime 证据缺口的真实状态
- 列横切缺口 C（本任务自身）
- 列任务 11a 拖拽落地、任务 11c 跨设备会话延续对本任务的依赖
- 列后端 sync_service 当前状态（是否已有 sync_log 表；是否已有 device_id 字段；是否已有 user_id 隔离查询）
- 列移动远控桌面的协议差分：当前是否有 device pairing、remote command、command audit、permission scope、revocation、local-mode deny 相关实现

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
2. 若启用 Rust IPC 数据面，在 `commands/sync.rs` 接入真实 pending-record 序列化：从 SQLite 读 `status='pending' LIMIT 100`，按时序排序；未启用时继续 fail-closed
3. 重写 `services/sync_engine.rs` 的 `push_pending_records`：读取 pending records → POST → 解析 `{accepted: [id...], rejected: [{id, reason}]}` → 批量更新本地状态
4. 后端 `routes/sync.py` push 路由：校验 Bearer Token → 校验每条 record 的 entity 归属 user → 路由到对应 service upsert → 写 `sync_log` → 返回结果
5. 单测：mock SQLite + mock HTTP，覆盖 全部 accepted / 全部 rejected / 部分 accepted 三种路径

### Step 4 · P0-3 pull（云端 → SQLite）

1. 重写 `services/sync_engine.rs` 的 `pull_incremental_updates`：从 `sync_state` 读 `last_sync_version` 作为 `since_version`，GET `/api/v1/sync/pull?since_version=X&limit=500`
2. 后端 `routes/sync.py` pull 路由：`SELECT * FROM sync_log WHERE user_id = ? AND version > ? ORDER BY version LIMIT 500`
3. 桌面端把响应按 entity_type 路由写入对应本地表（cases / contracts / documents / messages / ...）
4. 写完后 `sync_state['last_sync_version'] = max(version)`
5. 若启用 Rust IPC 数据面，在 `commands/sync.rs` 真正解析响应并写回；未启用时继续禁止假成功
6. 单测：覆盖 空响应 / 单 entity / 多 entity 混合 / 跨 user 不返回别人数据 三种路径

### Step 5 · P0-4 冲突合并

1. 新建 `desktop/src/services/conflict_resolver.rs`
2. pull 写回时检查 `local.updated_at` vs `remote.updated_at`：
   - remote 更新 → 直接覆盖（last-writer-wins 默认）
   - local 更新且与 remote 冲突 → 写入 `conflicts` 表（包含 local_payload + remote_payload + entity_type + entity_id），前端展示
3. 复用 `commands/sync.rs:155 resolve_conflict` 上行接口让用户手动选择
4. 单测：覆盖 仅本地改 / 仅云端改 / 双方都改时间戳同 / 双方都改本地新 / 双方都改云端新 五种路径

### Step 6 · P0-5 后端隔离 + P0-6 自动重试 + P0-7 加密 + P0-8 远程命令

1. 后端：sync_service push / pull 全部加 `user_id` 过滤（fail-closed，未传 user_id 直接 401）
2. 后端：限流按 `device_id + user_id` 维度（防恶意刷），用现有 Redis 限流中间件
3. 桌面：新建 tokio background task `retry_failed_tasks`：每 60s 扫描 + 指数退避；超 24h 标 `needs_human`
4. 桌面：SQLite 接 sqlcipher，密钥经 keyring；绝密模式强制加密；非绝密模式可选
5. 远程命令：新增 mobile -> desktop command queue，命令状态进入本地 SQLite 和后端审计；桌面端确认后执行，高风险动作二次确认；用户撤销配对后所有未执行命令过期

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
- **远程控制**：移动端远控桌面在绝密模式下默认拒绝；允许时必须桌面端显式配对和授权，所有命令有过期时间、可取消、可审计，不能让手机静默读取本地文件或密钥
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
- [ ] 跨设备会话续接：`scripts/cross-device-continuation-smoke.sh` 已补代码级 rehearsal，覆盖桌面 push、web/mobile pull、uni-mobile reply、桌面增量 pull 无丢失/重复；仍需 signed desktop package、共享预发账号和真实/官方移动设备 runtime 证据
- [ ] 移动远控命令队列：后端 fail-closed API 契约已有 `backend/tests/test_remote_control_fail_closed.py` 覆盖；仍需设备配对、命令入队、桌面确认、状态回传、取消/撤销、过期、审计和绝密模式拒绝的真实 runtime smoke
- [ ] 桌面 `cargo test` 新增至少 15 个用例全绿；后端 `pytest` 新增至少 10 个用例全绿；全栈 273 baseline 不退化
- [ ] 性能基线达标：push 100 条 P95 < 2s；pull 500 条 P95 < 3s
- [ ] `docs/audit/11b-sync-engine/01..05.md` + `docs/desktop/sync-engine-{design,protocol,runbook}.md` 全部产出
- [x] 经验沉淀到 hierarchical-memory（add-feature ≥ 1 + add-bugfix ≥ 1）
- [ ] `PROJECT_STATUS.md` 横切缺口 C 标记移除；`PRODUCT_ROADMAP.md` M3 状态更新

2026-05-09 hierarchical-memory 沉淀记录：已写入 `feature-1778335818500`（`desktop-sync-engine-sqlcipher-loopback`），记录 Rust-owned SQLCipher/keyring 本地库、`offline_tasks`/`sync_log` schema、push/pull/conflict/retry 编排、后端 SyncLog、packaged-binary sync smoke、unsigned release loopback 和跨设备续接代码级 rehearsal；已写入 `bugfix-1778335818498`，记录旧桌面同步 IPC 容易把空 payload/假成功误当真实数据面的根因和 fail-closed + SQLCipher 数据面 + packaged smoke 的修复模式。`find-feature "desktop sync engine SQLCipher loopback offline queue push pull conflict retry"` 与 `find-bugfix "desktop sync false success empty payload sqlcipher fail closed"` 均可检索。

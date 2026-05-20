# TASK-08a 案件 + 任务

> 波次 3 · 工时估 3-4 天
> 前置依赖：任务 0、任务 1（认证 + 权限）、任务 6（对象存储抽象层 — 案件证据落盘需要）
> 兄弟任务：任务 8b（找律师 + 案源市场 + 律所端）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`../00-platform/03-cross-cutting-gaps.md`

---

## 1. 范围

### 要碰的文件
- 后端服务层：
  - `backend/src/services/case_service.py`
  - `backend/src/services/task_service.py`
  - `backend/src/services/team_service.py`
  - `backend/src/services/timesheet_service.py`
- 后端路由：
  - `backend/src/api/routes/cases.py`
  - `backend/src/api/routes/tasks.py`
  - `backend/src/api/routes/approvals.py`
- 前端：
  - `frontend/src/pages/Cases.tsx`
  - `frontend/src/pages/CaseCenter.tsx`
  - `frontend/src/pages/CaseDetail.tsx`
  - `frontend/src/pages/Tasks.tsx`
  - `frontend/src/components/case-management/`
- 测试：
  - `backend/tests/test_case_service.py`
  - `backend/tests/test_comprehensive_flow.py`

### 不要碰的文件
- 找律师 / 案源市场 / 律所端任意文件（任务 8b）
- `backend/src/services/document_service.py`（任务 6 已处理）
- `payment_service` / `subscription` / `billing`
- `frontend/src/lib/design-tokens.ts`
- `backend/src/prompts/`

---

## 2. 必修 P0（带文件:行号 + 期望状态）

| # | 关键位置 | 现状 | 期望 |
|---|---|---|---|
| P0-1 | `case_service.py` 状态流转方法 | 2026-05-06 已补 `CASE_STATUS_TRANSITIONS`：`pending → in_progress → under_review/completed → closed`，非法跳转抛 `ValueError`，API 转 409，`closed/cancelled` 终态只读 | 显式状态机：`new → assigned → in_progress → submitted → reviewed → archived/closed`；非法跳转抛 4xx；闭合后只读 |
| P0-2 | `task_service.py` + `routes/tasks.py` 查询/更新接口 | 2026-05-06 已在服务层按 `created_by/assignee_id/admin` 过滤列表、详情、更新、删除、流转和批量流转；同组织非 owner/非 assignee 返回空/404 | 服务层强制 `(owner_id == current_user) OR (current_user in collaborators) OR (admin)`；写正反向用例 |
| P0-3 | `case_service.py` + `task_service.py` + 关联事件源 | 2026-05-06 `add_event()` 新增 `event_at` 入参并落到现有 `CaseEvent.event_time`，时间线按事件实际时间倒序；本轮无 schema 变更，历史 backfill 不需要代码迁移 | 统一使用 `event_at`（事件实际发生时间）做时序；对老数据补 backfill 脚本 |

---

## 3. 流程（Step 0-6）

### Step 0 · PRD vs 代码差分（强制）
产出 `docs/audit/08a-case-task/00-prd-reality-gap.md`：
- PRD/PROJECT_STATUS 中"案件状态机已完成"vs 实测可绕过性
- "任务 owner 收口"是否在路由层与服务层都加了过滤
- "时间线一致性"在 CaseDetail 页面是否真按事件时间显示

### Step 1 · 检索复用
- `/hierarchical-memory find-feature "状态机 transition 校验"`
- `/hierarchical-memory find-bugfix "owner 越权 任务查询"`
- `/iterative-retrieval` 按 路由 → 服务 → 模型 → 前端 → 测试 分层读

### Step 2 · 状态机 + 越权收口
- 在 case_service / task_service 抽出 `Transition` 表（from_state, to_state, allowed_roles）
- 越权检查统一到 service 层装饰器/依赖；路由层不再判定
- 写测试：5 类用户角色 × 6 种状态 × 4 种动作 矩阵

### Step 3 · 时间线一致性
- 统一事件 schema：`event_at` / `event_type` / `actor_id` / `case_id`
- 改 case 详情接口聚合：合同 / 审批 / 任务 / 时间记录 → 单一时间线
- 补 alembic 迁移：缺 `event_at` 的旧记录用 `created_at` 回填

### Step 4 · 验证回路
- `/verification-loop`：pytest（新增越权 + 状态机用例 ≥ 20）+ tsc + lint + build
- `/security-review`：对照 PROJECT_STATUS 越权钉子
- Playwright：案件创建 → 分派 → 提交 → 审核 → 归档全流程一遍

### Step 5 · 测试加固
- 把 `test_case_service.py` 与 `test_comprehensive_flow.py` 补到覆盖：
  - 非法跳转（archived → in_progress）拒绝
  - 任务 owner 之外用户查不到
  - 时间线 event_at 与 created_at 不一致时显示哪个

### Step 6 · 沉淀
- `add-feature --name "case_state_machine_v2" --pattern "Transition 表 + 装饰器收口"`
- `add-bugfix --symptom "task owner 越权" --fix "service 层强制过滤"`
- 写完后 `save-session anxin "TASK-08a 完成 — 案件 / 任务收口"`

---

## 4. 输出物

```
docs/audit/08a-case-task/
├─ 00-prd-reality-gap.md
├─ 01-prd-coverage.md
├─ 02-issues.md
├─ 03-fixes.md           (附状态机图)
├─ 04-test-additions.md  (含 5×6×4 矩阵覆盖率)
└─ 05-followups.md
```

附加：
- `docs/audit/08a-case-task/state-machine.md`（含 mermaid 状态图）

---

## 5. 风险护栏

- **schema 改动**：改案件 / 任务表必须给 alembic 迁移 + 回滚脚本；event_at backfill 脚本需在 staging 跑一遍
- **不破坏老 API**：状态机收紧可能让旧客户端的"创建即跳过"失败；先在 staging 灰度 7 天
- **owner 收口边界**：管理员旁路要保留，但写白名单审计日志
- **时间线一致性**：改聚合接口不要破坏分页；前端兼容 `event_at` 缺失走 `created_at` 兜底
- **不动**：找律师 / 案源 / 律所（任务 8b）；payment / billing；prompts；设计 tokens
- **测试基线**：不允许新增失败用例；baseline 273 → 仅可上调

---

## 6. 完成标准（DoD）

- [x] `case_service.py` 显式状态机 + 核心非法跳转/终态只读测试全绿
- [x] 非法跳转一律服务层拒绝，API 返回 409；状态变更写 `status_change` 事件
- [x] `task_service.py` 越权用例：非 owner / 非 assignee / 跨组织 全部 404 或空集
- [x] 时间线接口统一按事件实际时间 `event_time/event_at` 时序；前端沿用 `event_time`
- [ ] alembic 升级 + 回滚双向跑通；event_at backfill 脚本在 staging 跑过
- [ ] 后端 pytest 全绿（baseline → 新增 ≥ 20 用例）；前端 build 无新增警告
- [ ] Playwright 案件全流程一遍跑通
- [ ] `docs/audit/08a-case-task/01..05.md` + 状态机 mermaid 图全部产出
- [ ] 经验沉淀到 hierarchical-memory（add-feature + add-bugfix 至少各 1 条）

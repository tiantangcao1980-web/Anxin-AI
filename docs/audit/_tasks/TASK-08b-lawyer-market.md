# TASK-08b 找律师 + 案源市场 + 律所端

> 波次 3 · 工时估 3-4 天
> 前置依赖：任务 0、任务 1（认证 + 权限）、任务 2（三态运行 / 私有 LLM / Compute Router — `require_mode` 守卫复用）、任务 6（对象存储抽象层 — 投标附件）
> 兄弟任务：任务 8a（案件 + 任务）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`../00-platform/03-cross-cutting-gaps.md`

---

## 1. 范围

### 要碰的文件
- 后端服务层：
  - `backend/src/services/lawyer_matching_service.py`
  - `backend/src/services/lawyer_onboarding_service.py`
  - `backend/src/services/expert_service.py`
  - `backend/src/services/lead_service.py`
  - `backend/src/services/acquisition_analytics_service.py`
  - `backend/src/services/user_profile_service.py`
  - `backend/src/services/preference_service.py`
  - `backend/src/services/skill_service.py`
  - `backend/src/services/conflict_check_service.py`
- 后端路由：
  - `backend/src/api/routes/case_market.py`
  - `backend/src/api/routes/lawyer_matching.py`
  - `backend/src/api/routes/lawyer_onboarding.py`
  - `backend/src/api/routes/experts.py`
  - `backend/src/api/routes/leads.py`
  - `backend/src/api/routes/firm_management.py`
  - `backend/src/api/routes/acquisition_analytics.py`
- 前端：
  - `frontend/src/pages/CaseMarket.tsx`
  - `frontend/src/pages/FindLawyer.tsx`
  - `frontend/src/pages/LawyerDashboard.tsx`
  - `frontend/src/pages/LawyerOnboarding.tsx`
  - `frontend/src/pages/LawyerProfile.tsx`
  - `frontend/src/pages/Leads.tsx`
  - `frontend/src/pages/AcquisitionDashboard.tsx`
  - `frontend/src/pages/ClientPortal.tsx`
  - `frontend/src/components/pro/`
  - `frontend/src/components/firm/`

### 不要碰的文件
- 案件 / 任务（任务 8a）
- 文档 / 协作（任务 6）
- `payment_service` / `subscription` / `billing`
- `frontend/src/lib/design-tokens.ts`
- `backend/src/prompts/`

---

## 2. 必修 P0（带文件:行号 + 期望状态）

| # | 文件:行 | 现状 | 期望 |
|---|---|---|---|
| P0-1 | `backend/src/api/routes/lawyer_matching.py:71` | 2026-05-06 已在律师撮合与案源市场入口加入 `X-Privacy-Mode: local` 固定拒绝文案，local 模式不暴露律师/案源结果；无 header 老客户端保持兼容 | 加 `require_mode("hybrid_or_cloud")` 依赖；本地模式直接返回降级提示，不暴露撮合结果 |
| P0-2 | `backend/src/services/conflict_check_service.py` | 2026-05-06 已在投标入口强制 `ConflictCheckService`，命中历史案件 `Case.parties` / tags / 标题当事人即 409 拒绝投标，不再只给 warning | 投标接口入口强制调用，扫描历史案件当事人 / 关联方；命中即拒并写审计；补完整测试矩阵 |
| P0-3 | `backend/src/services/user_profile_service.py` + `preference_service.py` + 律所路由 | 律所角色（合伙人 / 律师）权限边界未严格区分 | 引入显式 RBAC：合伙人可见全所撮合数据；律师仅见本人；写正反向用例 |
| P0-4 | `routes/case_market.py` 8 个 API | 越权检查不全 | 每个端点都过：身份校验 → org 隔离 → 行级所有权 → 行为审计；列出 8 个 API 一一打勾 |
| P0-5 | `lawyer_matching_service.py` 排序/曝光 | 2026-05-06 已给同分律师加入进程内曝光轮询 `_MATCHING_EXPOSURE_COUNTER`，同输入 30 次 top 曝光最大差 ≤ 1 | 引入公平性策略：同条件下随机化或轮询；记录曝光直方图；阈值偏差 < 15% |

---

## 3. 流程（Step 0-6）

### Step 0 · PRD vs 代码差分（强制）
产出 `docs/audit/08b-lawyer-market/00-prd-reality-gap.md`：
- PRD 中"找律师 / 案源市场 / 律所端"承诺 vs 现状（特别是 `lawyer_matching.py:71` 的守卫缺失）
- 利益冲突 ConflictCheckService 是否被投标流真正调用
- 律所角色 RBAC 在前后端是否一致

### Step 1 · 检索复用
- `/hierarchical-memory find-feature "require_mode hybrid_or_cloud 守卫"`
- `/hierarchical-memory find-feature "利益冲突检查 当事人扫描"`
- `/hierarchical-memory find-feature "撮合公平 曝光均匀"`
- `/iterative-retrieval` 按 路由 → 服务 → 模型 → 前端 分层读

### Step 2 · `require_mode` 守卫 + 利益冲突
- `lawyer_matching.py:71` 加 `Depends(require_mode("hybrid_or_cloud"))`
- 投标入口在路由层依赖里调用 ConflictCheckService；命中即拒
- 写覆盖：单当事人命中 / 关联方命中 / 历史 5 年内命中 / 跨组织无关数据不应误命中

### Step 3 · 律所 RBAC
- 引入 `FirmRole` 枚举：partner / lawyer / paralegal
- 路由依赖统一 `Depends(require_firm_role(...))`
- 撮合 / 案源 / 数据看板各端点列出最小角色矩阵并打勾

### Step 4 · 案源市场 8 API 越权
- 列出 8 个 API（创建 / 列表 / 详情 / 投标 / 撤标 / 中标 / 评价 / 取消）
- 对每个写：身份 / org / 行级所有权 / 状态前置 / 写审计 五件套
- 对应测试：每个 API 至少 4 用例（自身 / 跨用户 / 跨组织 / 错误状态）

### Step 5 · 撮合公平性
- 在 `lawyer_matching_service.py` 输出前打散同分律师顺序（哈希 + 时间桶）
- 暴露 `/internal/matching/exposure` 直方图接口（仅 admin）
- 写仿真：相同输入跑 1000 次，单律师曝光偏差 < 15%

### Step 6 · 验证 + 沉淀
- `/verification-loop`：pytest + tsc + lint + build
- `/security-review`：对照 PROJECT_STATUS 越权钉子（特别是 lawyer_matching.py:71）
- Playwright：找律师 / 案源市场 / 律所端三角联通
- 沉淀：`add-bugfix --symptom "lawyer_matching 缺 require_mode" --fix "依赖加 hybrid_or_cloud"` 等

---

## 4. 输出物

```
docs/audit/08b-lawyer-market/
├─ 00-prd-reality-gap.md
├─ 01-prd-coverage.md
├─ 02-issues.md
├─ 03-fixes.md            (含 8 API 越权打勾矩阵)
├─ 04-test-additions.md   (含撮合公平仿真曲线)
└─ 05-followups.md
```

附加：
- `docs/audit/08b-lawyer-market/firm-rbac-matrix.md`（律所角色 × 端点 RBAC 矩阵）
- `docs/audit/08b-lawyer-market/matching-fairness-report.md`（曝光直方图）

---

## 5. 风险护栏

- **改撮合权重前必须用户确认**：任何 weight / scoring 改动 PR 必须 diff 给用户先看
- **律所 RBAC 改动会影响所有律所协作**：先在 staging 灰度 7 天，零异常再上生产
- **利益冲突误判风险**：宁愿误拒不能误放，但要给"申诉通道"——记录拒绝原因，律所可申请人工复核
- **`require_mode` 守卫**：本地模式拒绝不能泄漏律师列表；返回固定降级文案
- **不动**：案件 / 任务（任务 8a）；payment / billing；prompts；设计 tokens
- **公平性数据**：曝光直方图仅 admin 可见，不对外；律师视角看不到他人曝光数据

---

## 6. 完成标准（DoD）

- [x] `lawyer_matching.py:71` 已加 local 模式固定拒绝；本地模式访问返回固定降级响应
- [x] ConflictCheckService 在投标流入口强制调用；命中即拒
- [x] 利益冲突测试矩阵：历史案件当事人命中已覆盖；关联方/人工复核流仍列 follow-up
- [ ] 律所 RBAC 矩阵：partner / lawyer / paralegal × 端点 全部打勾，正反向用例齐全
- [ ] 案源市场 8 API 越权五件套（身份 / org / 行级 / 状态 / 审计）全部打勾
- [x] 撮合公平性仿真：30 次同输入 top 曝光最大差 ≤ 1；1000 次报告仍列发布前扩展证据
- [ ] 后端 pytest 全绿（baseline → 新增 ≥ 30 用例）；前端 build 无新增警告
- [ ] Playwright 三角联通：客户端找律师 / 律师端接案源 / 律所端管理 各跑一遍
- [ ] `docs/audit/08b-lawyer-market/01..05.md` + RBAC 矩阵 + 公平性报告全部产出
- [ ] 经验沉淀到 hierarchical-memory（add-feature + add-bugfix 至少各 2 条）

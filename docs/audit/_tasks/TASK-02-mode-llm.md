# 任务 02 — 三态运行 + 私有 LLM + V2 路由真分离

> 波次：1 / 工时估：3-4 天 / 负责人：待分配
> 必读前置：../PLAN.md、../00-platform/01-prd-reality-gap.md、../00-platform/03-cross-cutting-gaps.md

## 1. 范围

### 要碰的文件
- 后端：
  - `backend/src/services/private_llm_service.py`、`compute_router_service.py`、`feature_flag_service.py`、`sync_service.py`、`llm_service.py`
  - `backend/src/api/routes/offline_packs.py`、`feature_flags.py`、`sync.py`、`updates.py`、`llm.py`
  - `backend/src/api/routes/due_diligence.py`、`lawyer_matching.py`、`im.py` 及各 Pro 路由（加 `require_mode` 依赖）
  - `backend/src/middleware/`（新增 mode / subscription dependency）
- 前端：
  - `frontend/src/App.tsx`（重点 207 行 `/pro` 路由守卫）
  - `frontend/src/components/pro/ProLayout.tsx`（重点 30-68 行导航 path）
  - `frontend/src/components/mode/ModeGate.tsx`（重点 153 行）
  - `frontend/src/components/mode-switcher/`、`frontend/src/pages/PrivateLLMSetup.tsx`
  - `frontend/src/context/PrivacyContext.tsx`（重点 62-87 行）
- 桌面：
  - `desktop/src/models/`、`desktop/src/commands/local_llm.rs`

### 明确不要碰的文件（避免越界）
- `backend/src/api/routes/auth.py` 及登录链路（属任务 01）
- `backend/src/services/payment_service.py`、`subscription_service.py` 的支付实现（属任务 10；本任务仅消费 `can-use-mode` API）
- `desktop/src/commands/sync.rs` / `services/sync_engine.rs`（属任务 11b）
- `frontend/src/lib/design-tokens.ts`（设计系统不动）
- `backend/src/prompts/`（任何变更需用户预审）

## 2. 必修 P0（带文件:行号）

- [ ] **P0-1 `/pro` 路由加 `require_provider` 守卫**
  - 现状：`frontend/src/App.tsx:207` 仅 `<ProtectedRoute>`，任意登录用户可进入服务方端
  - 期望：新增/复用 `<RequireProvider>` 包裹（基于 `user.role === 'lawyer' | 'lawfirm_admin'` 或 `primary_client === 'pro'`）；未通过 → 跳 `/` 或 `/pro/login` 提示
- [ ] **P0-2 ProLayout 导航 path 全部迁到 `/pro/*`**
  - 现状：`frontend/src/components/pro/ProLayout.tsx:30-68` 全部 `to` 指向根路径（`/case-center` / `/management` / `/chat` / `/find-lawyer` 等）
  - 期望：全部改为 `/pro/case-center`、`/pro/management`、`/pro/chat`、`/pro/find-lawyer` 等；并补齐 `App.tsx` 中 `/pro/*` 子路由
- [ ] **P0-3 ModeGate "切换运行模式"按钮不允许直接 setMode**
  - 现状：`frontend/src/components/mode/ModeGate.tsx:153` `onSwitchMode` 直接 `setMode(PrivacyMode.HYBRID)`，无订阅校验、无确认弹窗
  - 期望：改为调用 `requestModeSwitch(target)`；无订阅 → 弹订阅引导；用户取消 → 不切换
- [ ] **P0-4 PrivacyContext 失败兜底改 fail-closed**
  - 文件：`frontend/src/context/PrivacyContext.tsx:62-87`
  - 73 行：`json?.data?.allowed ?? true` → `?? false`
  - 82-86 行：catch 块中**禁止 setMode**；改为 `return false` + UI 提示"无法验证订阅，请稍后重试"
- [ ] **P0-5 PrivacyContext 默认端口与全项目对齐**
  - 文件：`frontend/src/context/PrivacyContext.tsx:68`，将 `http://localhost:8003/api/v1` 改为 `8001`（与 Vite proxy / api client 一致）；最好统一从 `import.meta.env.VITE_API_BASE_URL` 读取
- [ ] **P0-6 LLM 配置组织隔离修复（S-104 退化）**
  - 文件：`backend/src/services/llm_service.py:288` `if org_id:` → `if org_id is not None:`
  - 更安全：拆分为 `list_all_configs(superuser_only=True)` + `list_by_org(org_id: UUID)` 两个方法，调用方明确语义
  - 文件：`backend/src/api/routes/llm.py:177` 同步调整调用：非 superuser 一律走 `list_by_org` 且 `org_id` 必传，否则 403
- [ ] **P0-7 后端模式守卫依赖**
  - 期望：实现 `require_mode(*allowed: PrivacyMode)` FastAPI dependency；混合/云端能力路由必须显式声明
  - 落点：`backend/src/api/routes/due_diligence.py`、`lawyer_matching.py`、`im.py`、Pro 相关路由（含舆情/资讯/找律师/匿名聊天等需联网能力）

## 3. 流程

### Step 0 — PRD vs 现实差分
读 `../00-platform/01-prd-reality-gap.md` 第 1.1 / 1.2 节 + 第 2 节 S6 行；列出"已确认事实" vs "需要进一步核查"，写入 `docs/audit/02-mode-llm/00-prd-reality-gap.md`。

### Step 1 — hierarchical-memory find-bugfix
关键词：`route guard provider role`、`mode gate bypass`、`privacy fail-open default`、`org_id is None falsy bug`、`localhost port mismatch frontend`、`require_mode fastapi dependency`。

### Step 2 — 分层读取（路由 → 服务 → 模型 → 前端 → 测试）
1. `frontend/src/App.tsx`（路由树）→ `components/pro/ProLayout.tsx` → 各 Pro 子页面
2. `frontend/src/components/mode/ModeGate.tsx` + `mode-switcher/` + `context/PrivacyContext.tsx`
3. `backend/src/api/routes/llm.py` → `services/llm_service.py`（追 `_apply_org_filter` / `list_configs` 全部调用点）
4. `backend/src/services/{private_llm_service,compute_router_service,feature_flag_service}.py`
5. `backend/src/middleware/`（已有 dependency 模式）
6. 后端测试：`backend/tests/test_llm_*.py`、`test_business_authorization_guards.py`；前端 e2e：`frontend/e2e/role-access.spec.ts`、`mode-*.spec.ts`（如有）

### Step 3 — code-review + security-review
关注点：守卫遗漏（每条 Pro 路由是否都被 `<RequireProvider>` 包裹）/ ModeGate 还有哪些直接 setMode 的入口 / PrivacyContext fail-closed 是否会让"网络抖动 = 全员被锁"（需要给重试 + 缓存最近一次合法 allowed 值，例如 5min）/ org_id 过滤的所有调用方是否都修了。

### Step 4 — 先写失败测试再改实现（每个 P0 都必须）
- P0-1/P0-2：e2e `pro-route-guard.spec.ts`（普通用户访问 `/pro` → 被踢回 `/`；ProLayout 点任意菜单不跳出 `/pro` 树）
- P0-3：组件测试 `ModeGate.test.tsx`（点击切换按钮 → 必须调用 `requestModeSwitch`，不能直接 `setMode`）
- P0-4：`PrivacyContext.test.tsx`（mock fetch 返回 `{}` → `allowed === false`；mock fetch reject → 不切换且返回 false）
- P0-6：`backend/tests/test_llm_org_isolation.py`（普通用户 `org_id=None` → 不能列出他人配置；superuser → 可列全部）
- P0-7：`test_require_mode_dependency.py`（本地模式调云端能力 API → 403；混合模式 → 通过）

### Step 5 — verification-loop
- `cd backend && pytest -k "llm or mode or privacy or pro or guard"`
- `cd backend && pytest`（不退化当前默认 `354 passed, 1 skipped` 基线）
- `cd frontend && npm run lint && npm run typecheck && npm run build`
- `cd frontend && npx playwright test e2e/role-access.spec.ts`
- 手测：以普通用户登录访问 `/pro` 应被拦；服务方账号进入 `/pro` 后菜单点击不应跳出

### Step 6 — simplify + 沉淀到 hierarchical-memory
- `add-bugfix --symptom "/pro 路由壳无 provider 守卫" --fix "RequireProvider + 子路由迁移" --files ...`
- `add-bugfix --symptom "PrivacyContext 失败默认放行" --fix "?? false + catch 不切换" --files ...`
- `add-bugfix --symptom "if org_id 漏 None 分支" --fix "is not None + 拆方法" --files ...`
- `add-feature --name "require_mode 依赖" --pattern "FastAPI Depends 统一守卫" --files ...`

## 4. 输出物（写到 `docs/audit/02-mode-llm/`）
- `00-prd-reality-gap.md`
- `01-prd-coverage.md`
- `02-issues.md`
- `03-fixes.md`
- `04-test-additions.md`
- `05-followups.md`
- 代码 PR（直接修复 P0；P1/P2 标记为 followup）

## 5. 风险护栏（必须遵守）
- 改 `compute_router_service` 默认策略前先与用户确认；本任务仅做"守卫 + fail-closed"，不调路由策略权重
- ModeGate / PrivacyContext 改动会影响所有线上用户的运行模式体验，PR 必须含灰度方案（feature flag 逐步放量）
- `/pro` 路由迁移要兼容已收藏老链接：从根路径访问命中守卫时若用户是 provider 自动 301 到 `/pro/...`，避免"老书签全 404"
- 不动 `prompts/` 任意文件
- 不动 `.env`、不动 `design-tokens.ts`
- 桌面端 `local_llm.rs` 改动不允许触发自动更新通道（属用户专管）

## 6. 完成标准（DoD）
- [ ] 全部 7 个 P0 修复，每个有"失败 test → 通过 test"证据
- [ ] 后端 `pytest` 不退化（当前默认 `354 passed, 1 skipped` 基线）；新增 `test_llm_org_isolation` + `test_require_mode_dependency`
- [ ] 前端 `lint` + `build` + `playwright test` 不退化
- [ ] 6 份文档（`00..05.md`）齐全
- [ ] 沉淀到 hierarchical-memory 至少 2 条（建议 P0-4 + P0-6）
- [ ] PR 描述含 ModeGate / PrivacyContext / 路由迁移的灰度方案 + 回滚预案
- [ ] 回写 `../00-platform/01-prd-reality-gap.md` 表 1.1 / 1.2 / 第 2 节 S6 状态

# 任务 01 — 认证 + 权限 + CAPTCHA 收口

> 波次：1 / 工时估：3-4 天 / 负责人：待分配
> 必读前置：../PLAN.md、../00-platform/01-prd-reality-gap.md、../00-platform/03-cross-cutting-gaps.md

## 1. 范围

### 要碰的文件
- 后端：
  - `backend/src/api/routes/auth.py`、`backend/src/api/routes/security_challenge.py`
  - `backend/src/services/user_service.py`、`backend/src/services/oauth_service.py`、`backend/src/services/pii_service.py`、`backend/src/services/captcha_service.py`、`backend/src/services/sms_service.py`、`backend/src/services/email_service.py`
  - `backend/src/middleware/`（Redis 故障 fail-closed 中间件 / 守卫）
  - `backend/src/models/user*.py`（重置 token 表 / 索引）
- 前端：
  - `frontend/src/pages/Login.tsx`
  - `frontend/src/components/auth/`
  - `frontend/src/lib/store.ts`（重点 272 / 281 / 285 行）
  - `frontend/src/hooks/`（auth 相关）
- 测试：
  - `backend/tests/test_auth_*.py`、`backend/tests/test_business_authorization_guards.py`
  - `frontend/e2e/auth.spec.ts`、`frontend/e2e/role-access.spec.ts`

### 明确不要碰的文件（避免越界）
- `backend/src/services/payment_service.py` / `subscription_service.py`（属任务 10）
- `backend/src/api/routes/llm.py` / `llm_service.py`（属任务 02）
- `backend/src/services/esign_service.py`（属任务 05）
- `frontend/src/components/mode/`、`frontend/src/context/PrivacyContext.tsx`（属任务 02）
- `backend/src/api/routes/anonymous_chat.py`（属任务 09）
- `backend/src/prompts/`（任何 prompt 文件改动需用户预审）

## 2. 必修 P0（带文件:行号）

- [ ] **P0-1（S2）密码重置码升级为高熵单次 token + 上下文绑定**
  - 现状：6 位数字，可枚举空间 10^6
  - 期望：≥128bit 高熵随机 token；单次有效；过期 ≤15min；绑定用户 + 请求 IP/UA hash + 渠道
  - 文件：`backend/src/api/routes/auth.py`、`backend/src/api/routes/security_challenge.py`、`backend/src/services/user_service.py`
  - 2026-05-06 状态：后端已完成。高熵 token、单次消费、15min 过期、IP/UA hash 与 email/channel 绑定已落地；`_reset_tokens` 已迁移到 `password_reset_tokens` DB 表，仅存 SHA-256 hash，并带 Alembic `028_password_reset_tokens`。
- [ ] **P0-2（S3）前端 access/refresh token 不再写 localStorage**
  - 现状：`frontend/src/lib/store.ts:272,281,285` 直写 localStorage + `persist({name:'auth-storage'})` 双重落盘
  - 期望：refresh token 走 httpOnly + Secure + SameSite=Lax cookie；access token 仅内存（或 IndexedDB + AES-GCM）；移除 persist 中的 token 字段
  - 必须：老用户迁移方案（首次进入新版本 → 静默 silent-refresh 一次将旧 token 升级，不能让全部用户被强退）
  - 2026-05-06 状态：Web 源码已完成。`frontend/src` 不再读写 auth token localStorage；浏览器 access token 仅内存；refresh token 走 HttpOnly cookie；后端 refresh body 兼容默认关闭，仅 `AUTH_REFRESH_BODY_COMPAT_ENABLED=true` 临时开启。仍需移动端/桌面端策略复核。
- [ ] **P0-3（S4）Redis 故障下认证 fail-closed**
  - 期望：登录速率限制、CAPTCHA 状态、refresh token 黑名单/会话表 在 Redis 不可用时**拒绝服务**而非放行；返回 503 + `Retry-After`
  - 文件：`backend/src/middleware/`、`backend/src/services/auth/`
  - 2026-05-06 状态：认证敏感 rate-limit 入口已支持 fail-closed，staging/production 自动启用，开发/测试可用 `AUTH_REDIS_FAIL_CLOSED=true` 演练；refresh token blacklist fail-closed 已补回归。剩余：CAPTCHA/session-table 等 Redis 状态面逐项审计。
- [ ] **P0-4（S10）CAPTCHA 全覆盖**
  - 现状：仅登录/注册/忘记密码入口
  - 期望：重发短信验证码、重发邮箱验证码、重置密码提交 三个入口同样必须 CAPTCHA
  - 文件：`backend/src/api/routes/auth.py`（resend / reset 各入口）+ 前端对应组件
  - 2026-05-06 状态：重发邮箱验证码与重置密码提交已强制 CAPTCHA，前端也会传递 CAPTCHA token；短信验证码入口仍需确认是否存在独立 resend API。
- [ ] **P0-5 store.ts 双重持久化清理**
  - 现状：手动 `localStorage.setItem` + `persist({name:'auth-storage'})` 同时存在
  - 期望：单一来源；登出时一次清空；与 P0-2 联动
  - 文件：`frontend/src/lib/store.ts`
  - 2026-05-06 状态：Web 已完成。`auth-storage` 只持久化 user/isAuthenticated；token 由 `TokenStorage` 内存快照管理，登出统一走 `clearAuth()` 清理旧 key。

## 3. 流程

### Step 0 — PRD vs 现实差分
读 `../00-platform/01-prd-reality-gap.md` 第 2 节（钉子表）S2/S3/S4/S10 行；列出"已确认事实"vs"需要进一步核查"，写入 `docs/audit/01-auth/00-prd-reality-gap.md`。

### Step 1 — hierarchical-memory find-bugfix
关键词：`reset code 6-digit`、`localStorage token xss`、`redis fail-open auth`、`captcha resend bypass`、`refresh token httpOnly cookie 迁移`。命中即复用经验。

### Step 2 — 分层读取（路由 → 服务 → 模型 → 前端 → 测试）
1. `backend/src/api/routes/auth.py` + `security_challenge.py`（重置/验证码/CAPTCHA 入口）
2. `backend/src/services/user_service.py` + `captcha_service.py` + `sms_service.py` + `email_service.py`
3. `backend/src/middleware/`（速率限制、Redis 适配）+ `backend/src/services/auth/`
4. `backend/src/models/user*.py`（password_reset_token 表）
5. `frontend/src/lib/store.ts` → `pages/Login.tsx` → `components/auth/`
6. `backend/tests/test_auth_*.py`、`frontend/e2e/auth.spec.ts`、`role-access.spec.ts`（含 6 个 skipped 用例）

### Step 3 — code-review + security-review
关注点：token 熵 / 单次性 / 绑定上下文 / Redis 失败语义 / cookie 属性（httpOnly + Secure + SameSite + Path） / CSRF 配套（双 token 或同源 + SameSite）/ 老用户迁移路径无中断。

### Step 4 — 先写失败测试再改实现（每个 P0 都必须）
- P0-1：`test_password_reset_token_high_entropy`、`test_reset_token_single_use`、`test_reset_token_context_bound`
- P0-2：e2e `auth-token-not-in-localstorage.spec.ts`；后端 `test_refresh_token_via_cookie`
- P0-3：`test_auth_fail_closed_when_redis_down`（mock redis 抛错 → 期望 503）
- P0-4：`test_captcha_required_on_resend_and_reset`
- P0-5：e2e `auth-store-single-source-of-truth.spec.ts`

### Step 5 — verification-loop
具体命令：
- `cd backend && pytest -k "auth or reset or captcha or redis_fail"`
- `cd backend && pytest`（不退化当前默认 `354 passed, 1 skipped` 基线）
- `cd frontend && npm run lint && npm run build`
- `cd frontend && npx playwright test e2e/auth.spec.ts e2e/role-access.spec.ts`
- 复活 `role-access.spec.ts` 中 6 个 skipped 用例

### Step 6 — simplify + 沉淀到 hierarchical-memory
- `add-bugfix --symptom "6-digit reset code 可枚举" --fix "高熵 token + 单次 + 上下文绑定" --files ...`
- `add-bugfix --symptom "token in localStorage XSS 风险" --fix "httpOnly cookie + 内存 access + 静默迁移" --files ...`
- `add-feature --name "Redis 故障 fail-closed 守卫" --pattern "中间件统一拒绝并返回 503" --files ...`

## 4. 输出物（写到 `docs/audit/01-auth/`）
- `00-prd-reality-gap.md`
- `01-prd-coverage.md`
- `02-issues.md`
- `03-fixes.md`
- `04-test-additions.md`
- `05-followups.md`
- 代码 PR（直接修复 P0；P1/P2 标记为 followup）

## 5. 风险护栏（必须遵守）
- 改 JWT 算法 / cookie 策略 / token 存储位置 → PR 提交前必须用户预审
- 老用户迁移方案必须明确写入 PR：是否需要全员重新登录、是否能静默 silent-refresh、回滚方案如何
- 不动 `.env` / 不轮换密钥（属任务 0）
- 不动 `prompts/` 任意文件
- 不允许 force push、不动已发布 commit
- Redis fail-closed 上线前要在 staging 跑 chaos test（手动 kill redis）

## 6. 完成标准（DoD）
- [ ] 全部 5 个 P0 修复，每个有"失败 test → 通过 test"证据
- [ ] 后端 `pytest` 不退化（当前默认 `354 passed, 1 skipped` 基线）
- [ ] 前端 `npm run build` + `playwright test` 不退化；`role-access.spec.ts` 6 个 skipped 至少复活 4 个
- [ ] 6 份文档（`00..05.md`）齐全
- [ ] 沉淀到 hierarchical-memory 至少 2 条（建议 P0-1 + P0-2）
- [ ] PR 描述含老用户迁移路径 + 回滚预案
- [ ] 回写 `../00-platform/01-prd-reality-gap.md` 第 2 节 S2/S3/S4/S10 状态

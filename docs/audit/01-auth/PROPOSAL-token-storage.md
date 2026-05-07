# 提案：前端 token 存储升级 + store 双重持久化清理

> 关联：TASK-01-auth.md P0-2 / P0-5；00-platform/01-prd-reality-gap.md S2/S3/S4/S10/S8
> 性质：实施方案（不含代码改动）
> 作者：Claude Code（审计）
> 日期：2026-05-04

---

## 1. 现状盘点

### 1.1 frontend 中 access_token / refresh_token 全部使用点

| 文件:行 | 类型 | 说明 |
|---|---|---|
| `frontend/src/lib/store.ts:274` | write | `setToken` 直写 `localStorage.setItem('access_token', ...)` |
| `frontend/src/lib/store.ts:281` | write | `login` 直写 localStorage |
| `frontend/src/lib/store.ts:285-286` | clear | `logout` 同时移除 `access_token` 和 `refresh_token` |
| `frontend/src/lib/store.ts:290` | persist | `persist({name:'auth-storage'})` 把整个 auth state（含 token）再次写入 localStorage |
| `frontend/src/lib/api.ts:1203/1296/1508/1574/2170` | read | 5 处直接读 localStorage 拼 Authorization 头 |
| `frontend/src/lib/api.ts:123` | write | refresh 后用 `storage.setAccessToken` 写回（已走抽象层） |
| `frontend/src/lib/api.ts:167-168` | type | LoginResponse 包含两个明文 token |
| `frontend/src/lib/platform/storage.ts:3-4` | abstraction | `TokenStorage` 抽象层（已存在！Tauri 走 plugin-store + browser 走 localStorage） |
| `frontend/src/lib/client/auth-client.ts:35-39` | write | 登录后写入 `storage.setAccessToken` + `storage.setRefreshToken` + `persistDesktopAuth` |
| `frontend/src/components/auth/ProtectedRoute.tsx:70` | read | 守卫直接 `localStorage.getItem('access_token')` |
| `frontend/src/components/auth/AdminRoute.tsx:18` | read | 同上 |
| `frontend/src/components/chat/PaymentPanel.tsx:85,124` | read | 支付组件直读 |
| `frontend/src/components/chat/SigningWorkflowPanel.tsx:77` | read | 电签组件直读 |
| `frontend/src/context/PrivacyContext.tsx:64` | read | 模式上下文直读 |
| `frontend/src/hooks/useFeatureFlag.ts:13` | read | feature flag hook 直读 |
| `frontend/src/hooks/useIMWebSocket.ts:60,71` | fixed | ✅ 2026-05-06 已改为内存 token + WS 首包 `auth` 鉴权，不再拼 URL token |
| `frontend/src/pages/Login.tsx:197,209` | write | 登录页两处 `setAuth(resp.user, resp.access_token)` |
| `frontend/src/pages/Collaboration.tsx:318` | read | 协同页直读 |
| `frontend/src/pages/admin/AdminFeatureFlags.tsx:141` | read | 管理页直读 |
| `frontend/src/pages/admin/AdminAudit.tsx:92` | read | 审计页直读 |
| `frontend/src/pages/admin/AdminHarness.tsx:15` | read | Harness 管理页直读 |
| `frontend/src/components/templates/TemplateWizard.tsx:178,243` | read | 直读 `auth_token`（**注意：错误的 key，孤儿代码**） |

**结论**：直读 `access_token` 共 **15 处**；写入共 **6 处**（store.ts 3 处 + auth-client 1 处 + Login.tsx 2 处经由 setAuth）；已有抽象层 `lib/platform/storage.ts`，但前端只有部分代码使用。

### 1.2 frontend 中 localStorage 全部使用点（按用途分类）

| 用途 | 文件:行 | key |
|---|---|---|
| **token（敏感）** | store.ts、api.ts、ProtectedRoute、AdminRoute、useIMWebSocket 等 15+ 处 | `access_token` / `refresh_token` |
| **错误 token key（孤儿）** | TemplateWizard.tsx:178/243 | `auth_token`（疑似旧迭代残留） |
| **用户偏好** | UserProfile.tsx:205/241 | `notifications_enabled` |
| **缓存（非敏感）** | UserProfile.tsx:221/252 | `user_info`（用户基本信息缓存） |
| **UI 偏好** | Layout.tsx:203/223 | `HEADER_ACTION_LABELS_KEY` |
| **离线资源状态** | OfflineResourceManager.tsx:109/113 | `offline_resource_${id}` |
| **业务计数** | workflowConfig.ts:305/318 | 工作流使用统计 |
| **引导关闭记忆** | Guidance.tsx:127/136、V2MigrationGuide.tsx:67/74 | 关闭一次后不再展示 |
| **协作占位 ID** | Collaboration.tsx:215/217 | `user_id` / `username`（前端自生成游客名） |
| **persist 框架** | store.ts (zustand persist `auth-storage`、其他 store 的 conversations 等) | 多个 store name |

**结论**：除 token 外，约 9 类 18 处非敏感用途，**升级方案不应误伤**。

### 1.3 后端当前 token 签发 / 校验流程

- `backend/src/core/security.py:121-125` `create_token_pair` 同时签发 `access_token`（默认 120 分钟，见 `config.py:39 JWT_EXPIRE_MINUTES`）+ `refresh_token`（默认 7 天，`security_config.py:129` 上限 30 天）。
- `backend/src/core/security.py:342-365` `refresh_access_token` 单次有效（旧 refresh 立即拉黑名单 fail-closed）。
- `backend/src/core/deps.py:299-367` `get_current_user_*` 通过 `HTTPBearer` 从 `Authorization` 头读 access_token；**当前不读 cookie**。
- `backend/src/middleware/hmac_signature.py:73` 也从 `Authorization: Bearer` 头读 token。

### 1.4 现有 cookie 使用情况

后端已经在登录 / refresh / OAuth 三处把 **refresh_token 写 HttpOnly cookie**（见 `backend/src/api/routes/auth.py:271-278/534-541/646-653`，属性：`httponly=True, secure=not DEV_MODE, samesite="lax", max_age=REFRESH_TOKEN_EXPIRE_MINUTES*60`），并支持从 cookie 或 body 读取（`auth.py:507`）。`auth.py:587` logout 时 `delete_cookie("refresh_token")`。

CORS（`backend/src/core/security_config.py:60-67`）：`allow_credentials=True` + `allow_origins` 白名单 + `allow_headers=["Authorization","Content-Type","X-Request-ID"]`，已具备跨源带 cookie 的条件。

**结论**：后端 refresh_token httpOnly 化已完成 80%，前端 fetch 也已 `credentials: 'include'`（`api.ts:119`）。**真正没做的是 access_token 的存储**——它仍然在 localStorage 里，被 15 处代码直读。

---

## 2. 关键决策

### 2.1 目标方案选择

#### 选项 A：access_token 也走 httpOnly cookie + refresh_token httpOnly cookie（最严格）
- 后端 `/auth/login` 同时 Set-Cookie 两个 cookie；`get_current_user_*` 改为既能读 Header 也能读 Cookie（兼容期）。
- 前端不再读 token；axios 全局 `withCredentials: true`；Authorization 头退役。
- 必须配套 CSRF：SameSite=Lax + 双 token (CSRF token in JS-readable cookie + 同名头)；非 GET 请求都加 `X-CSRF-Token`。
- WebSocket：同源时 cookie 自动带上（浏览器规范）；跨源需用 `Sec-WebSocket-Protocol` 子协议或首包消息鉴权。
- Tauri / 移动 webview / 小程序：`tauri://` 自定义 scheme 浏览器对 cookie 处理不一致，需走"首次握手换 short-lived token"或保持 Bearer 头降级。

#### 选项 B：access_token in-memory（zustand 不持久化）+ refresh_token httpOnly cookie（推荐）
- 刷新页面 → 走 `/auth/refresh`（cookie 已携带 refresh_token）→ 拿到新 access_token 注入内存 → 继续。
- access_token 存在内存 = `useAuthStore.getState().token`，**不写 localStorage、不写 sessionStorage**。
- XSS 即使能跑代码也只能拿到内存里那一份，刷新后即清；refresh_token 在 httpOnly cookie 里 JS 读不到 → 拿不到长期凭证。
- 不需要 CSRF（access 仍走 Authorization 头，攻击者拿不到 token；refresh 端点配 CSRF token + same-site=lax 即可）。

#### 选项 C：localStorage + Web Crypto AES-GCM 加密
- 密钥仍要存某处（IndexedDB 或派生自 fingerprint），任何能跑 JS 的攻击者都能解，**安全增益有限，复杂度高**。

**推荐：选项 B**。理由：
1. 后端已经做了 refresh httpOnly cookie 80%，沉没成本低。
2. 不需要重写 `get_current_user_*`（仍读 Bearer）+ 不引入 CSRF 工程量。
3. 解决 S3 P0（XSS 拿不到 refresh）+ S8 P0（access_token 不在 localStorage 后，IM ws 可改首包鉴权）。
4. Tauri / 桌面 / 小程序兼容性最好——它们仍可走 Bearer，无需折腾各端 cookie 行为差异。
5. 后续若要进一步收紧，可在 B 之上再叠加 A（access 也 cookie 化）作为可选硬化。

### 2.2 老用户迁移策略

- **双 token 期 = 14 天**：上线后前 14 天，`/auth/refresh` 同时接受
  - cookie 中的 refresh_token（新版本）
  - 旧版本残留在 localStorage 里、客户端附带的 body / Authorization 中的 refresh_token
- 第 1 天上线后，旧版本前端首次访问 `/auth/refresh` → 后端在响应里 Set-Cookie 写入 refresh_token（即把旧版本无感升级）。
- 第 14 天后，关闭 body 兼容路径，仅 cookie。
- **不能让全员强退**——成本估算：DAU × 重新登录摩擦（~30 秒/人）+ 客服压力 + 移动端 / 桌面端不在线用户首次启动失败。
- 回滚：每一步 PR 都加 feature flag（`AUTH_TOKEN_STORAGE_MODE` 环境变量：`legacy` / `cookie_refresh` / `memory_access`），出问题立即降级。

---

## 3. 实施分步方案（每步独立 PR）

### Step 1：清理 store.ts 双重持久化
- **改动**：删除 `setToken`/`login`/`logout` 中的 `localStorage.setItem('access_token',...)` / `localStorage.removeItem(...)`；`persist({name:'auth-storage'})` 的 `partialize` 显式只持久化 `user`，不持久化 `token`。
- **配套**：`Login.tsx:197/209` `setAuth` 调用不动；写入由 `auth-client.ts` 的 `storage.setAccessToken` 单点完成。
- **风险等级**：低
- **改动行数**：store.ts ~10 行（删 + partialize 1 行）；Login.tsx 0 行；测试新增 1 个 spec
- **风险点**：刷新页面后内存 token 丢失 → 必须依赖 Step 3 的 silent-refresh，否则会立刻退出登录。**故 Step 1 必须与 Step 2/3 同 sprint，不能单独上线**。

### Step 2：把 zustand `auth-storage` persist 切到不存 token + 增加内存 fallback
- **改动**：`useAuthStore` 加 `partialize: (s) => ({ user: s.user })`，token 字段从持久化中剔除；`hydration` 后由 `auth-client` 静默 refresh 注入。
- **风险等级**：中
- **改动行数**：store.ts ~5 行；新增一个 `useEffect` 在 App 启动时调 `silentRefresh`（~20 行）
- **风险点**：hydration 时序——若 ProtectedRoute 在 silent-refresh 完成前就拦截，会闪一下 login 页；需加 loading 态。

### Step 3：后端 `/auth/login` & `/auth/refresh` 兼容期双发（cookie + body）
- **改动**：`auth.py` 已有 `set_cookie` 调用（line 271/534/646），保持 body 中也返回 `access_token`（已是现状）；新增 `AUTH_TOKEN_STORAGE_MODE` flag，`legacy` 时连 refresh_token 也保留在 body，`cookie_refresh` 时仅 cookie + body 兼容字段。
- **配套**：`get_current_user_*` 暂不改（仍读 Bearer），仅为下一步预留——可加一个 `_read_access_from_cookie_or_header` 帮助函数，但默认走 header。
- **风险等级**：低（增量、向后兼容）
- **改动行数**：auth.py ~15 行（flag + 双发逻辑）；新增 4 个 pytest（cookie 签发 / cookie 校验 / silent refresh / fail-closed）
- **风险点**：CORS 已 `allow_credentials=True`，Origin 白名单要包含全部前端域名（含 staging / preview）。

### Step 4：前端把 15 处直读 `localStorage.getItem('access_token')` 全部改走 `getTokenStorage()` 抽象
- **改动**：批量替换；`ProtectedRoute` / `AdminRoute` / `useIMWebSocket` / 4 个 admin 页面 / 2 个 chat 组件 / `PrivacyContext` / `useFeatureFlag` / `Collaboration` / `api.ts` 5 处。
- **配套**：抽象层接口已存在（`lib/platform/storage.ts`），但同步 vs 异步要权衡——15 处中多数是同步上下文（render 中用），需在 store 中暴露 `tokenSync`（内存值的 React hook 形式）。
- **风险等级**：中（散点改动多，回归面广）
- **改动行数**：约 40-60 行 + 单测覆盖
- **风险点**：`useIMWebSocket.ts:71` 是 S8 P0，本步必须**同时**把 `?token=` 移除（参见 Step 5），不要先单纯改读取来源。

### Step 5：WebSocket（IM）切首包 token 鉴权
- **改动**：前端不再 `?token=` 拼 URL；连接成功 onopen 后第一帧发 `{"type":"auth","token":"..."}`；后端在 `accept()` 后 `await receive_json()` 校验首包 token，未通过 close(4001)。
- **配套**：与 TASK-10 P0-4 合并 PR；nginx 日志不会再出现 token；浏览器历史也不会。
- **风险等级**：中
- **改动行数**：useIMWebSocket.ts ~15 行；后端 ws 路由 ~20 行；e2e 1 个
- **风险点**：握手时序——首帧到达前后端如果有 5s 内未鉴权应主动断开；需要 watchdog timer。

### Step 6：删除 localStorage 旧 key + 关闭 body 兼容
- **改动**：上线 14 天后，前端 `migration.ts` 启动时显式 `localStorage.removeItem('access_token')` + `localStorage.removeItem('refresh_token')` + `localStorage.removeItem('auth_token')`（孤儿 key）；后端关闭 `legacy` flag。
- **风险等级**：低
- **改动行数**：~10 行
- **风险点**：埋点观测——上线后必须有 metric 显示 `legacy refresh path 使用率 < 0.1%` 才能关。

---

## 4. 兼容性矩阵

| 端 | cookie 行为 | 推荐路径 | 备注 |
|---|---|---|---|
| 浏览器（同源 / 子域） | 自动携带 | 选项 B 完美 | SameSite=Lax 足够 |
| 浏览器（跨源） | 需 `withCredentials` + CORS allow_credentials | 已就绪 | 注意 Origin 白名单维护 |
| Tauri（桌面） | 自定义 scheme `tauri://` 对 cookie 处理不一致 | 仍走 Bearer + plugin-store（已实现，见 `platform/storage.ts:157-240`） | 不强切 cookie |
| 移动端 React Native（如有） | 需手动 cookie jar | 走 Bearer + secure storage | 与 Tauri 同模式 |
| 微信小程序 | 不支持标准 cookie | 走 Bearer + wx.setStorageSync | 单独适配 |

**结论**：选项 B 对各端兼容性最好；Tauri/RN/小程序保留 Bearer 路径不动。

---

## 5. 测试方案

### 后端 pytest
- `test_login_sets_refresh_cookie_with_httponly_secure_samesite`
- `test_refresh_via_cookie_succeeds_without_body`
- `test_refresh_old_token_blacklisted_after_use`
- `test_login_legacy_mode_returns_refresh_in_body`（兼容期）
- `test_logout_deletes_refresh_cookie`

### 前端 Playwright e2e
- `auth-token-not-in-localstorage.spec.ts`：登录 → `evaluate(() => localStorage.getItem('access_token'))` === null
- `auth-store-single-source-of-truth.spec.ts`：检查 `auth-storage` 持久化字段不含 token
- `auth-page-refresh-still-logged-in.spec.ts`：刷新页面 → silent-refresh → 仍登录
- `auth-ws-no-token-in-url.spec.ts`：检查 ws URL 不含 `?token=`

### 手工
- 双 token 期切换、回滚演练、Tauri 端冒烟

---

## 6. 工时估算

| Step | 工时 |
|---|---|
| Step 1：store.ts 双重持久化清理 | 0.5 天 |
| Step 2：persist partialize + silent-refresh hydration | 1 天 |
| Step 3：后端双发 cookie + flag | 1 天 |
| Step 4：15 处直读改走抽象 | 2 天 |
| Step 5：WebSocket 首包鉴权（与 TASK-10 P0-4 合并） | 1.5 天 |
| Step 6：旧 key 清理 + flag 切换 | 0.5 天 |
| 合计 | **6.5 天**（不含双 token 期 14 天观测） |

---

## 7. 风险护栏

- **影响面**：所有线上用户登录态。
- **必须双 token 期**：≥14 天；期间任何回滚不应导致已升级用户被强退。
- **每步独立 PR + 灰度**：staging 跑通再灰度 5% → 25% → 100%。
- **Tauri / 自定义 scheme 行为差异**：Tauri 不切 cookie，保留 plugin-store + Bearer，不要为统一而牺牲桌面端可用性。
- **CSRF**：选项 B 不强引入；若未来叠加选项 A，必须同步加 CSRF token + 双提交校验。
- **观测**：上线后必须有指标
  - `auth.refresh.via_cookie_total` / `auth.refresh.via_body_total`（确认旧链路占比下降）
  - `auth.silent_refresh.success / fail`
  - `auth.token_in_localstorage_observed`（前端埋点；预期 7 天后归零）
- **不动**：`.env`（属任务 0）、`prompts/`、JWT 密钥轮换。
- **预审**：Step 3 / Step 5 涉及后端协议变更，PR 提交前必须用户预审；Step 4 散点改动量大，建议拆 2-3 个子 PR 评审。

---

> 完成此提案后，对应 TASK-01-auth.md P0-2 / P0-5 的"老用户迁移路径无中断"验收点。

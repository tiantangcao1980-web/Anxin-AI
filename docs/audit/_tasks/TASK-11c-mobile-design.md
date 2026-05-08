# TASK-11c 移动端 + 小程序 + 设计系统跨平台校验

> 波次 4 · 工时估 4-5 天
> 前置依赖：任务 0（密钥治理 SOP）、任务 1（认证 + token 存储 → 移动端 / 小程序登录链路依赖）、任务 11b（同步引擎 → 跨设备会话延续直接依赖）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`../00-platform/03-cross-cutting-gaps.md`、`PRODUCT_ROADMAP.md` M3（移动端 Beta）+ M4（多端闭环）、`DESIGN.md` 跨平台一致性章节、`frontend/src/lib/design-tokens.ts`

> 2026-05-08 定位补充：移动端是随身智能助手，也是桌面主工作站的远程控制端。移动端必须能继续桌面会话、审批高风险动作、查看桌面任务状态，并在安全配对后远程控制桌面执行工作。

---

## 1. 范围

### 要碰的文件

- 移动端：
  - `mobile/app/approvals/[id].tsx`（去掉静默 catch 的 fallback 数据）
  - `mobile/app/cases.tsx`（同类 fallback 模式排查）
  - `mobile/app/(tabs)/index.tsx`、`mobile/app/(tabs)/chat.tsx`、`mobile/app/settings.tsx`（去掉首页假数据兜底与误导性 mock 标记）
  - `mobile/app/_layout.tsx`（底部 Tab + safe-area-inset 校验）
  - **新建/预留** `mobile/app/desktop-control/`（设备配对、桌面状态、远程命令、取消/撤销、审计记录）
  - `mobile/components/`（按钮 / 卡片 / 列表项最小点击区 44px）
  - `mobile/lib/design-tokens.ts`（如不存在则新建，引用规则与 frontend 对齐）
- 小程序：
  - `mini-program/src/pages/profile/index.tsx`（去掉生产 mock_token）
  - `mini-program/src/pages/index/index.tsx`（去掉假新闻 fallback，改空状态）
  - `mini-program/src/services/`（登录链路对齐）
  - `mini-program/src/styles/design-tokens.*`（如存在则校验对齐）
- 设计系统：
  - `frontend/src/lib/design-tokens.ts`（**只读，不动**）
  - 各端的 token 实现（按规则对齐）
  - 新建 `docs/design/cross-platform-token-drift.md`（漂移清单）

### 不要碰的文件

- `frontend/src/lib/design-tokens.ts`（设计 tokens 全局唯一源，**未经用户同意不动**）
- `desktop/`（任务 11a / 11b 处理）
- `backend/src/prompts/`
- payment / billing / subscription 任意文件
- `frontend/src/lib/store.ts`
- 任何 secret / `.env`
- 跨设备会话延续的同步协议字段（任务 11b 已定义，本任务只调用）
- 桌面端远程命令执行细节（任务 11a/11b 处理；本任务只做移动端交互与 API 调用）

---

## 2. 必修 P0（带文件:行号 + 期望状态）

| # | 文件 | 现状 | 期望 |
|---|---|---|---|
| P0-1 | `mobile/app/_layout.tsx` + `mobile/components/` | 底部 Tab 与最小点击区可能未对齐 ROADMAP "44px / safe-area-inset" 要求 | 底部 Tab 对齐 iOS HIG / Material 3：高度 49pt（含 safe-area-bottom）；所有可点元素最小命中区 44×44pt；`useSafeAreaInsets` 全 Page 应用 |
| P0-2 | `mobile/app/approvals/[id].tsx` | ✅ 2026-05-06 已修：出错时不再用 fallback 假审批 | 详情页已改为 loading/error/empty 三态；`getDetailLoadErrorMessage` 覆盖 401 / 403 / 404 / network；错误态提供重试按钮 |
| P0-2 | `mobile/app/cases.tsx`（同模式） | ✅ 2026-05-06 复核：列表页已是 loading/error/empty 三态 | 加载失败时 `setCases([])` 并渲染错误 empty state + 重试按钮，不渲染假案件 |
| P0-2 | `mobile/app/(tabs)/index.tsx` / `chat.tsx` / `settings.tsx` | ✅ 2026-05-06 已修：首页不再以假任务/审批/通知兜底，聊天欢迎语不再作为假消息历史，设置页移除误导性 mock 标记 | 首页接口失败/为空时显示空状态；聊天欢迎语改为 `ListHeaderComponent`；移动端 mock/fallback grep 无命中 |
| P0-3 | `mini-program/src/pages/profile/index.tsx` | ✅ 2026-05-06 已修：生产环境不再注入 mock_token / 体验模式 token | 登录链路已改为：未登录 → `wx.login` + 后端 `/api/v1/auth/wechat/code2session` → 真实 JWT；失败给明确错误且不写入本地 token。后端新增 `WeChatMiniProgramOAuth.code2session`，不下发 `session_key` |
| P0-4 | `mini-program/src/pages/index/index.tsx` | ✅ 2026-05-06 已修：加载失败/空列表不再渲染假新闻 fallback | 已改为明确空状态（"暂无资讯，下拉刷新重试"）+ `console.warn` telemetry；不再混淆假数据与真数据 |
| P0-5 | 新建 `docs/design/cross-platform-token-drift.md` | 缺漂移清单 | 用 `/designdna` 校验：列出 desktop / mobile / mini-program 的 token 与 `frontend/src/lib/design-tokens.ts` 的差异；标 P0/P1/P2；**不重新设计**，仅产出清单 |
| P0-6 | `mobile/app/sessions/`（含跨设备会话延续入口） | 桌面开始 → 手机继续未实现 | 复用任务 11b 的 sync 协议；移动端拉 pull 后渲染当前活跃 session（含未读消息 + 未提交输入框草稿）；纯前端工作，不改后端协议 |
| P0-7 | `mobile/app/desktop-control/` + 11b remote command API | 后端已补远控 status/pairing/command fail-closed 契约，能拒绝未配置、绝密/本地模式、缺二次确认、缺配对、缺 route token 和缺队列/审计场景；移动端 UI、真实配对、命令队列和真机证据仍未实现 | 设备配对、桌面在线状态、远程命令下发、执行状态、取消/撤销、敏感动作二次确认和审计记录可见；绝密模式/未授权设备必须 fail-closed |

---

## 3. 流程（Step 0-5）

### Step 0 · PRD vs 代码差分（强制）

产出 `docs/audit/11c-mobile-design/00-prd-reality-gap.md`：
- ROADMAP M3（移动端 Beta）+ M4（多端闭环）vs 当前移动端 / 小程序实测能力差距
- PROJECT_STATUS 早期移动端测试基线 vs 代码现实（fallback 假数据掩盖真实错误）的差距
- 跨平台一致性：列三端 token 与 `design-tokens.ts` 漂移项
- 新定位差分：移动端作为随身助手和桌面远控端，当前是否具备设备配对、远程命令、状态回传、撤销、审计和隐私模式拒绝能力

### Step 1 · 检索复用

- `/hierarchical-memory find-feature "底部 Tab safe-area-inset 44px"`
- `/hierarchical-memory find-bugfix "静默 catch fallback 假数据"`
- `/hierarchical-memory find-feature "跨设备会话延续 sync"`
- `/iterative-retrieval` 按 移动端路由 → 页面 → 组件 → service → tokens / 小程序同上 分层读

### Step 2 · 移动端 P0-1 / P0-2 / P0-6 / P0-7

1. P0-1：审查 `mobile/app/_layout.tsx` 底部 Tab；对所有 Pressable / TouchableOpacity 最小命中区做 44pt 校验，必要时加 hitSlop；`SafeAreaProvider` 全局包裹
2. P0-2：grep `catch.*=>.*fallback|return.*\[\]|return mock` 找出所有静默 catch；逐一改为按 HTTP 状态分支 + empty state 组件
3. P0-6：移动端"会话列表"页加 sync pull 触发；活跃 session 渲染 pull 回的 last_message + draft（草稿来自任务 11b 同步队列）；不改后端协议
4. P0-7：新增桌面控制入口；展示已配对桌面、在线状态、当前任务、可执行命令、权限范围和审计历史；下发命令前展示风险说明，高风险动作必须二次确认；取消/撤销必须可见

### Step 3 · 小程序 P0-3 / P0-4

1. P0-3：grep `mock_token|fakeToken|TODO.*token` 全删；登录链路对齐：`wx.login` → `code2session` → 真实 jwt；失败明确弹错误（不要静默切 mock）
2. P0-4：grep `fallback.*news|mock.*news|假新闻`；改为 EmptyState 组件 + 错误 telemetry
3. 上线前确认后端 `/api/v1/auth/wechat/code2session` 接口真实工作（与任务 1 对齐）

### Step 4 · P0-5 设计系统跨平台校验

1. `/designdna` 在三端各跑一次：desktop（任务 11a 新增 `frontend/src/components/desktop/`）/ mobile（`mobile/`）/ mini-program（`mini-program/`）
2. 与 `frontend/src/lib/design-tokens.ts` 做 token 名 → 值的差异对照
3. 产出 `docs/design/cross-platform-token-drift.md`：分 P0（颜色 / 字号 / 间距 / 圆角不一致）/ P1（次要 token）/ P2（platform-specific 合理差异如 macOS vibrancy / iOS safe-area）
4. **本任务不修复漂移项**，仅产出清单。修复要走单独 PR + 用户审

### Step 5 · 验证 + 沉淀

- `/verification-loop`：
  - 移动端：`npm test`（baseline 10 → 至少 +3 用例覆盖错误分支）+ tsc + lint
  - 小程序：tsc + lint + 微信开发者工具预览
  - 全栈：273 baseline 后端测试不退化（理论上不应变化）
- 真机手测：iPhone 14 / Android 13 各跑一遍登录 / 审批 / 会话延续；微信开发者工具跑小程序登录
- `/security-review`：重点查 mock_token 是否真的全删 + 移动端是否还有静默 catch
- `add-bugfix --symptom "移动端静默 catch fallback 掩盖真实错误" --fix "按 HTTP 状态分明确分支 + empty state" --files ...`
- `add-bugfix --symptom "小程序生产环境 mock_token" --fix "对齐 wx.login 真实链路" --files ...`
- `add-feature --name "cross-platform-token-drift-audit" --pattern "designdna 三端校验产出漂移清单（不修）" --files ...`

---

## 4. 输出物

```
docs/audit/11c-mobile-design/
├─ 00-prd-reality-gap.md
├─ 01-prd-coverage.md
├─ 02-issues.md
├─ 03-fixes.md
├─ 04-test-additions.md
└─ 05-followups.md
```

附加：
- `docs/design/cross-platform-token-drift.md`（本任务的关键产出，**不含修复 patch**）
- `docs/mobile/error-handling-guidelines.md`（统一错误分支与 empty state 模式）

---

## 5. 风险护栏

- **不动 design-tokens**：`frontend/src/lib/design-tokens.ts` 在没有用户同意下不得修改；本任务只校验、只产清单
- **fallback 移除**：移除移动端静默 fallback 后，用户在弱网 / 后端故障时会看到更多空状态 / 错误页，**必须在 release notes 显式说明**，让用户知道"看到错误页 = 后端真的有问题，不是 app bug"
- **mock_token**：小程序 mock_token 移除前必须确认后端登录链路（任务 1 已交付）真实工作；否则会导致小程序登录全断；建议先在测试环境验证 7 天再发版
- **跨设备会话延续**：依赖任务 11b 的同步协议字段；任务 11b 未交付前本任务 P0-6 只能 mock 或延后（标 P1）
- **移动远控桌面**：依赖任务 11a/11b 的 host 与 command queue；未交付前不能用假成功 UI，必须显示“等待桌面端支持”或禁用入口
- **真机灰度**：iOS / Android 各灰度 50 用户跑 14 天，再扩量；微信小程序开"开发版 → 体验版 → 正式发布"三阶
- **不改后端**：本任务理论上不动 backend/；如发现移动端 fallback 是因后端缺接口，记到 followups.md 不在本任务修
- **不动**：desktop / payment / prompts / store.ts / 任务 11b 的同步协议
- **设计漂移修复**：发现的漂移项**不在本任务修复**，要走单独 PR 给用户先看 diff

---

## 6. 完成标准（DoD）

- [ ] 移动端底部 Tab 高度与最小触控 token 代码级对齐；`Layout.touchTarget.min=44`、Tab/EmptyState、小程序 `.action-item/.menu-item/.send-btn` 已接入；仍需真机逐项确认所有可点元素 44pt
- [x] `mobile/app/approvals/[id].tsx` + `mobile/app/cases.tsx` 静默 catch fallback 全部移除；HTTP 状态分支化错误处理。证据：`getDetailLoadErrorMessage` 单测、`rg "fallbackApproval\\b|fallback-approval" "mobile/app/approvals/[id].tsx" mobile/src/features/workflow` 无命中、`cases.tsx` 错误态已有重试 empty state
- [x] 移动端跑过 grep `catch.*fallback|mock.*data|TODO.*真数据|@mock-data FALLBACK|fallbackApprovals|fallbackApproval\\b|fallback-approval`，结果为空
- [x] 小程序 `mini-program/src/pages/profile/index.tsx` mock_token 完全移除；登录走 wx.login 真实链路。证据：`test_wechat_mini_code2session_requires_feature_flag`、`test_wechat_mini_code2session_issues_jwt_without_session_key`、`rg "mock_token_|登录成功（体验模式）|/auth/wechat-login" mini-program/src backend/src backend/tests` 对源码无命中、`cd mini-program && npm run build:weapp` 通过
- [x] 小程序 `mini-program/src/pages/index/index.tsx` 假新闻 fallback 改为 EmptyState 组件。证据：`rg "fallbackNews|mock 数据|假新闻|mock_token_|登录成功（体验模式）|/auth/wechat-login" mini-program/src backend/src backend/tests` 对源码无命中、`cd mini-program && npx tsc --noEmit --skipLibCheck --noUnusedLocals false` 通过、`cd mini-program && npm run build:weapp` 通过
- [x] `docs/design/cross-platform-token-drift.md` 产出三端 vs `design-tokens.ts` 漂移清单（P0/P1/P2 分级）；小程序语义 token 层和触控 token 底座已补，品牌主色最终统一方向仍待定
- [ ] 移动端跨设备会话延续：桌面开始一段对话 → 移动端 pull 后能看到 last_message + draft（依赖任务 11b 已交付）
- [ ] 移动端远程控制桌面：设备配对、桌面在线状态、命令下发、状态回传、取消/撤销、敏感动作二次确认和审计记录通过真机/模拟器 transcript；未授权或绝密模式下 fail-closed
- [x] 移动端测试 baseline 10 → 至少 +3（覆盖错误分支）；当前 `npm test` 为 `7 files / 19 tests passed`，`npx tsc --noEmit --module esnext` 通过；新增字符串 transport error、status 优先级错误分支、触控 token、弱网 refresh-token、`X-Privacy-Mode` 透传和 local 模式零网络调用用例
- [ ] 小程序 tsc + lint 全绿；微信开发者工具登录链路真机验证通过
- [ ] iPhone 14 + Android 13 真机手测通过：登录 / 审批 / 会话延续 三个用户故事
- [x] `docs/audit/11c-mobile-design/01..05.md` + `docs/design/cross-platform-token-drift.md` + `docs/mobile/error-handling-guidelines.md` 全部产出；另补 `00-prd-reality-gap.md`
- [x] release notes 已写"移除静默 fallback，看到错误页是真错"提示；草案为 `docs/release/mobile-error-state-release-notes.md`，正式发布前需合并到版本说明
- [ ] 经验沉淀到 hierarchical-memory（add-bugfix ≥ 2 + add-feature ≥ 1）

# 安心智能助手 · 实施方案（2026-05-22）

> 配套文档：[产品蓝图](2026-05-22-product-blueprint.md) · [DESIGN.md](../../DESIGN.md)
> 适用范围：本周（M1-M2）→ 下两周（M3-M6）→ 再下周（M7）
> 拆分原则：6 个 lane 并行，每个 lane 有明确写入范围 + 完成判据

---

## 0. Lane 总览

| Lane | 写入范围 | Owner | 阻断关系 |
|---|---|---|---|
| **L1 Design Tokens** | `frontend/src/index.css` · `frontend/tailwind.config.js` · `desktop/src/styles` · `mobile/src/constants/colors.ts` · `mobile/src/theme/*` · `mini-program/src/styles/design-tokens.*` · `apps/uni-mobile/src/styles/*` | Design + 前端 lead | 阻断 L3/L4/L5 |
| **L2 清理（品牌 / 死代码 / 旧文档）** | 全仓 grep 范围 + `docs/archive/` | 全员可参与 | 不阻断 |
| **L3 Desktop UI** | `frontend/src/components/layout/LayoutV3.tsx` · `frontend/src/pages/*` · `desktop/src/services/{tray,window-chrome}.rs` | 桌面 lead | 依赖 L1 |
| **L4 Mobile UI** | `mobile/app/(tabs)/*` · `mobile/src/{components,theme,features}` · `mini-program/src` · `apps/uni-mobile/src` | 移动 lead | 依赖 L1 |
| **L5 Web 瘦身** | `frontend/src/App.tsx` · `frontend/src/pages/_legacy/*` · 官网新增 `frontend/src/pages/marketing/*` | Web lead | 依赖 L1 |
| **L6 Backend 收口** | `backend/src/api/routes/{auth,sync,im}.py` · `backend/README.md` · `docs/openspec/` | 后端 lead | 不阻断 |

---

## L1 — 统一 Design Tokens（飞书风）

### 任务清单

1. **更新 `frontend/src/index.css`** — 把第 7 行 `安心法务` 注释改为 `安心智能助手`；新增 `--im-primary: 217 100% 55%`；圆角 `--radius-md: 8px` 改对应 `--radius-xl: 12px`；
2. **更新 `frontend/tailwind.config.js`** — `colors.imPrimary` token；`borderRadius.xl: 12px` 收一档；
3. **更新 `mobile/src/constants/colors.ts`** — `primary` 从 `#D4A574` 改为 `#F97316`；新增 `imPrimary: '#1664FF'`；
4. **更新 `mobile/src/theme/`**（`useV3Theme`）—— 暴露 `colors.imPrimary`；
5. **更新 `mini-program/src/styles/design-tokens.scss + .ts`** — 同步 primary + imPrimary；
6. **更新 `apps/uni-mobile/src/styles/`** — 同步；
7. **更新 `desktop/src/`** — Rust 端的 tray 颜色/icon 引用（如有）；
8. **新增 `docs/design/tokens.md`** — 单一 token contract 表（10.11 表的可机读版）。

### 写入边界

- 不动业务页代码；只动 token 源；
- 业务页若直接使用 `text-[#...]` 硬编码，本 lane 不修，由 L2 清理。

### 验收命令

```bash
# 1. 跨端 grep 残留旧色
rg "#D4A574|#E8C9A8|#B8895A" mobile apps mini-program | wc -l   # 期望 0
rg "安心法务" --type ts --type tsx --type scss --type css --type json --type py -g '!docs/archive' | wc -l   # 期望 0

# 2. 构建通过
cd frontend && npm run build
cd ../mobile && npm run typecheck
cd ../mini-program && npx tsc --noEmit
```

---

## L2 — 清理（旧品牌 / 死代码 / 旧文档）

### 文档归档

```bash
mkdir -p docs/archive/2026-05-22-pre-blueprint
git mv PROJECT_STATUS.md docs/archive/2026-05-22-pre-blueprint/
git mv PRODUCT_ROADMAP.md docs/archive/2026-05-22-pre-blueprint/
git mv ROADMAP.md docs/archive/2026-05-22-pre-blueprint/
git mv docs/plans/2026-05-09-workstation-admin-ia-boundary.md docs/archive/2026-05-22-pre-blueprint/
# 保留：docs/plans/2026-05-13-ui-ux-optimization-roadmap.md (作为本蓝图 UX 子计划)
```

### 旧品牌字符串

```bash
# frontend/src/index.css:7 注释改为「安心智能助手」
# backend/src/core/config.py:434  anxin-fawu.com → anxinai.com
# docs/release/commercial-delivery-readiness.md  历史引用保留，但标记为"v1/v2 时期"
```

### 律师 SaaS 残留代码

```bash
# 1. 归档前端页面（保留路由占位，但不再渲染业务内容）
mkdir -p frontend/src/pages/_legacy/lawyer-saas
git mv frontend/src/pages/LawyerOnboarding.tsx frontend/src/pages/_legacy/lawyer-saas/
git mv frontend/src/pages/LawyerDashboard.tsx frontend/src/pages/_legacy/lawyer-saas/
git mv frontend/src/pages/LawyerProfile.tsx frontend/src/pages/_legacy/lawyer-saas/
git mv frontend/src/pages/FindLawyer.tsx frontend/src/pages/_legacy/lawyer-saas/
git mv frontend/src/pages/CaseMarket.tsx frontend/src/pages/_legacy/lawyer-saas/
git mv frontend/src/pages/ClientPortal.tsx frontend/src/pages/_legacy/lawyer-saas/
git mv frontend/src/components/pro frontend/src/pages/_legacy/lawyer-saas/pro

# 2. 在 App.tsx 把这些路由重定向到 /download
# /pro/* → /download?ref=pro
# /find-lawyer /case-market /lawyer-onboarding /lawyer-dashboard /client-portal → /download

# 3. 删除残留组件
rm frontend/src/components/a2ui/components/LawyerReferralCard.tsx
```

### Mobile 老 tab 文件清理

```bash
# 已 href:null 隐藏，但文件还在；统一删除
git rm mobile/app/\(tabs\)/index.tsx
git rm mobile/app/\(tabs\)/chat.tsx
git rm mobile/app/\(tabs\)/collaboration.tsx
git rm mobile/app/\(tabs\)/investigation.tsx
git rm mobile/app/\(tabs\)/knowledge.tsx
git rm mobile/app/\(tabs\)/profile.tsx

# 重命名为飞书风
git mv mobile/app/\(tabs\)/personas.tsx mobile/app/\(tabs\)/workbench.tsx
# 新增 messages.tsx（消息 tab）
# capabilities 内容并入 me.tsx 高级能力子页
```

### 双布局合并

```bash
# 删除 frontend/src/components/Layout.tsx，统一用 LayoutV3
# 删除 frontend/src/App.tsx 里的 VITE_V3_NAV 开关
# 删除 frontend/src/components/ModuleLayout.tsx（已被 LayoutV3 替代）
```

### Backend 调试文件清理

```bash
mkdir -p backend/scripts/dev
git mv backend/debug_camel.py backend/scripts/dev/
git mv backend/debug_openai_direct.py backend/scripts/dev/
git mv backend/local_test.db backend/scripts/dev/   # 或直接删
git mv backend/create_test_db.py backend/scripts/dev/
git mv backend/verify_skills_e2e.py backend/scripts/dev/
git mv backend/verify_workforce.py backend/scripts/dev/
```

### 验收

```bash
rg "LawyerOnboarding|LawyerDashboard|LawyerProfile|FindLawyer|CaseMarket|ClientPortal" frontend/src --type tsx --type ts | grep -v _legacy | wc -l   # 期望 0
rg "VITE_V3_NAV" frontend | wc -l   # 期望 0
rg "安心法务" --type ts --type tsx --type py --type scss --type css -g '!docs/archive' | wc -l   # 期望 0
test ! -f frontend/src/components/Layout.tsx  # 期望 true
test ! -f frontend/src/components/ModuleLayout.tsx
```

---

## L3 — 桌面 UI（飞书工作台）

### 任务清单

1. **改造 `frontend/src/components/layout/LayoutV3.tsx`** 为三栏外壳：
   - 左导航条 56px：5 个一级模块（消息 / 任务 / 工作台 / 知识 / 设置）+ 用户头像
   - 中列表 280px：可拖拽 240-360；列表项规范见 DESIGN §10.5
   - 右内容：自适应
   - 底部状态栏 24px：模式 + 同步 + 在线 + ⌘K
2. **新增 `frontend/src/components/desktop/CommandPalette.tsx`** ⌘K
   - shortcut: `Cmd+K` / `Ctrl+K`
   - 输入框 + 分组结果（最近 / 智能体 / 任务 / 文档 / Skill / 跳转）
3. **新增 `frontend/src/components/desktop/StatusBar.tsx`**
   - 显示模式 / 同步状态 / 在线状态 / 命令面板入口
   - 同步冲突可点击跳转 `SyncConflicts` 页
4. **页面收敛**：当前 52 个页面在桌面端只暴露：
   - 一级 5 个：Messages / Tasks / Workbench / Knowledge / Settings
   - 二级 ~20 个：通过中列表选择项加载
   - 其余删除/重定向（见 L2）
5. **Tauri 端**：
   - `desktop/src/services/tray.rs` 托盘菜单文案与新 5 模块对齐
   - `desktop/src/services/window-chrome.rs` 顶部 chrome 高度 28/32（系统原生）
   - 全局快捷键 `Cmd+Shift+Space` 呼出（已有）保留

### 功能问题修复（伴随 UI 改造）

| 文件 | 问题 | 修复 |
|---|---|---|
| `frontend/src/components/mode-switcher/SyncStatus.tsx` | 冲突弹窗已改字段差异摘要，需验证 packaged runtime | 截图验证 |
| `desktop/src/services/sync_engine.rs` | 旧 fallback 已 fail-closed；packaged runtime push/pull 待跑通 | 跑通 SQLCipher push/pull |
| `frontend/src/components/Layout.tsx` 与 `LayoutV3.tsx` 双布局 | 删除旧布局 | L2 |
| `frontend/src/pages/Chat.tsx` 与桌面工作台不一致 | 改为三栏：会话列表 + 对话窗 + Artifact 抽屉 | UI 改 |

### 验收

```bash
cd desktop && cargo clippy --all-targets && cargo test
cd ../frontend && npm run lint && npm run test && npm run build
# 启动 dev server，验证：
#   - ⌘K 弹出命令面板
#   - 状态栏显示模式 + 同步
#   - 三栏布局符合 DESIGN §10.2
```

---

## L4 — 移动 UI（飞书移动端 + 远控）

### 任务清单

1. **改 `mobile/app/(tabs)/_layout.tsx`** 4 tab：
   - 消息（`MessageSquare`）
   - 任务（`ListChecks`）
   - 工作台（`LayoutGrid`，原 `personas.tsx`）
   - 我（`User`）
2. **新增 `mobile/app/(tabs)/messages.tsx`** 消息 tab：
   - 会话列表（人 / agent / 系统）
   - 远控授权请求 inline 显示（不要单独跳转）
3. **改 `mobile/app/(tabs)/me.tsx`**：
   - 账号 / 订阅 / 桌面配对 / 推送 / 隐私 / 高级（容纳原 capabilities 内容）
4. **NavBar / SafeArea 统一**：`mobile/src/components/Layout/`
5. **硬编码颜色迁移**：grep `style.*Color.*#` 改 token
6. **接口闭环**：`investigation.tsx` `knowledge.tsx` 已闭环（保留作为深链页）

### 远控授权 UI（飞书企微没有，但是我们需要）

- 触发：桌面登录新设备 → 移动端推送 → 消息流 inline 卡片
- 卡片含：设备名 / IP / 时间 / 「授权」/「拒绝」/「永远信任」三按钮
- 授权后桌面端登录成功；拒绝则桌面端登录失败
- 配套后端：`POST /im-pairing/control/*` 已有

### 验收

```bash
cd mobile && npm run typecheck && npm run test
# iOS Simulator 跑通：
#   - 启动 → 4 tab：消息 / 任务 / 工作台 / 我
#   - 工作台 10 personas 卡片
#   - 任务列表加载
#   - 桌面发起配对 → 移动收到推送 → 授权
bash scripts/mobile-ios-simulator-smoke.sh
```

---

## L5 — Web 瘦身为官网 + 后台

### 任务清单

1. **新增 `frontend/src/pages/marketing/`**:
   - `Home.tsx` 首页（产品介绍 + 下载入口）
   - `Features.tsx` 功能介绍
   - `Personas.tsx` 10 personas 介绍
   - `Download.tsx` 客户端下载
   - `Help.tsx` 帮助中心
2. **改 `frontend/src/App.tsx`**:
   - 根路由 `/` 渲染 `marketing/Home`
   - `/features` `/personas` `/download` `/help` `/pricing` 渲染 marketing 子页
   - `/chat` `/case-center` `/management` `/documents` 等业务路由 → `<Navigate to="/download?ref=xxx">`
   - `/admin/*` 保留
   - `/login` 保留（用于扫码激活客户端）
3. **新增 `frontend/src/components/marketing/MarketingLayout.tsx`** 官网布局（顶部 nav + footer）
4. **后台**：`AdminLayout` 已存在，确认 18 admin 页面可用
5. **删除 `/pro/*` 服务方端**

### 验收

```bash
cd frontend && npm run build && npm run e2e:local
# 验证：
#   - / 显示官网
#   - /chat → /download?ref=chat
#   - /admin → 登录后看到 18 页
#   - /pro/* → 410 或 redirect
```

---

## L6 — Backend 云服务收口

### 任务清单

1. **新增 `backend/src/api/routes/auth.README.md`** — 列出所有 auth 端点 + 请求/响应 + 错误码
2. **新增 `backend/src/api/routes/sync.README.md`** — 同上
3. **新增 `backend/src/api/routes/im.README.md`** — 同上 + WebSocket 协议
4. **新增 `docs/openspec/03-cloud-services-contract.md`** — 三个云服务对外契约总览
5. **验证 OpenAPI**：`backend/src/api/main.py` 生成的 `/openapi.json` 包含三个域的全部端点
6. **契约测试**：`backend/tests/contract/` 新增 / 补全 auth / sync / im 三个 spec 文件

### 功能修复（伴随收口）

| 路由 | 已知问题 | 修复 |
|---|---|---|
| `sync.py` | desktop fail-closed，packaged runtime push/pull 未跑通 | L3 联调 |
| `im.py` | WebSocket 在线状态推送未实装 | 实装 `presence` |
| `auth.py` | 多设备会话列表 + 撤销 | 补 endpoint |

### 验收

```bash
cd backend
ruff check src tests
mypy src
pytest tests/contract -x
# OpenAPI 三个域完整
python -c "from backend.src.api.main import app; import json; spec = app.openapi(); assert all(p.startswith(('/auth','/sync','/im','/im-pairing')) for p in spec['paths'] if 'auth' in p or 'sync' in p or 'im' in p)"
```

---

## 验证 + 上线门禁（M7）

### 全栈门禁

```bash
# 1. 静态质量基线
bash scripts/static-quality-baseline.sh

# 2. 商业 quick gate
bash scripts/commercial-readiness-gate.sh --quick

# 3. 跨端 smoke
bash scripts/mobile-device-smoke.sh
bash scripts/desktop-mvp-local-gate.sh
bash scripts/uni-mobile-smoke.sh

# 4. evidence
ls docs/release/evidence/   # 期望含本次升级的截图 / transcript
```

### Go/No-Go 判据

- L1 token 漂移 = 0
- L2 旧品牌残留 = 0（除归档）
- L3 桌面三栏 + 状态栏 + ⌘K 已上线，cargo + frontend build 通过
- L4 移动 4 tab 改名 + Simulator transcript
- L5 Web 官网 build 通过，/ 渲染 marketing
- L6 OpenAPI 三个域完整，契约测试通过
- `commercial-readiness-gate.sh --quick` 通过

---

## 时间表（建议 3 周）

| 周 | M | Lane |
|---|---|---|
| **W1** | M1-M2 | L1（token） + L2（清理）并行 |
| **W2** | M3-M4 | L3（桌面） + L4（移动） + L6（后端）并行 |
| **W3** | M5-M6 | L5（Web） + 全栈联调 |
| **W3 末** | M7 | 商业门禁 + 试点 |

---

## 风险与回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| 移动端把 `D4A574` 改成 `F97316` 后视觉差异大 | 通过 PR 一次性改 + 截图对比 | git revert |
| 删除老 tab 文件导致 expo-router 路由 404 | 删除前先全仓 grep 引用 | git restore |
| 双布局合并后部分页面引用旧 `Layout.tsx` | TypeScript 编译报错先暴露 | 编译失败回滚 |
| Web 业务路由重定向后老书签 404 | `<Navigate replace>` + `?ref=xxx` 留参 | 保留路由占位 |
| 后端 sync packaged runtime 跑不通 | 保留 fail-closed，evidence 标 pending | 不阻断 quick gate |

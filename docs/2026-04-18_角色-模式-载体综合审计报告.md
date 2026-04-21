# 安心法务角色/模式/载体综合审计报告

日期：2026-04-18

## 1. 审计目标

本次审计以项目现有业务载体与业务逻辑为出发点，围绕四个维度进行交叉验证：

1. 角色体系是否与产品设计、前端实现、后端鉴权一致。
2. 本地 / 混合 / 云端三态模式是否真正按业务规则生效。
3. Web / Desktop / Mobile / Mini Program 四类载体是否承载了同一业务真相。
4. 核心业务链路是否具备足够的自动化验证和可交付性证据。

审计方法同时结合：

- 设计系统执行审计：`frontend/scripts/design-audit.sh`
- 前端静态验证：`lint` / `build` / `vitest` / `playwright`
- 后端功能与权限验证：`pytest`
- 跨端壳层验证：`mobile vitest` / `mini-program build:h5` / `desktop cargo check`

## 2. 总体结论

当前项目的总体判断是：

- Web 主站已经具备较强的业务闭环能力，尤其在登录、导航、统一文档工作台、核心业务动作、基础权限拦截方面证据较强。
- 后端核心授权与主要业务 API 已达到可验证状态，主业务回归稳定。
- 设计方向基本正确，DesignDNA 的品牌基线已经建立，但全端执行一致性仍不够，存在明显 token 漂移、图标入口漂移和局部硬编码。
- 双客户端分离、三态模式、跨载体统一体验这三件事在“产品设计”层已经成立，但在“实现闭环”层还没有完全成立。

一句话结论：

**项目已经不是“原型不可用”，但距离“按角色、模式、载体完全一致地可交付”仍有一轮明显的产品工程化收口。**

## 3. 验证结果摘要

### 3.1 自动化与构建结果

| 类别 | 命令 | 结果 |
|---|---|---|
| 前端设计审计 | `npm run audit:design` | 成功，发现多处设计系统漂移 |
| 前端静态检查 | `npm run lint` | 通过 |
| 前端构建 | `npm run build` | 通过，存在大 chunk 警告 |
| 前端单测 | `npm run test` | `3/3` 通过 |
| 前端 E2E 全量 | `npm run test:e2e` | `108 passed`, `46 skipped` |
| 前端角色/业务专项 E2E | `npm run test:e2e -- role-access.spec.ts business-actions.spec.ts` | `14/14` 通过 |
| 后端全量 | `pytest backend/tests` | `273/273` 通过 |
| 后端核心业务授权专项 | 核心回归组合 | `42/42` 通过 |
| 后端性能基准 | `pytest backend/tests/test_performance_benchmark.py` | `8 passed`, `1 failed` |
| 移动端单测 | `cd mobile && npm run test` | `10/10` 通过 |
| 小程序 H5 构建 | `cd mini-program && npm run build:h5` | 通过 |
| 桌面端检查 | `cd desktop && cargo check` | 通过 |

### 3.2 性能信号摘要

前端生产构建成功，但存在明显大包信号：

- `vendor-three`: 1.32 MB
- `vendor-livekit`: 552 KB
- `vendor-recharts`: 487 KB
- `vendor-editor`: 473 KB
- `Chat` 页面 chunk：206 KB

后端性能基准中，缓存写入平均耗时 `10.54ms`，高于测试阈值 `10ms`。

## 4. 按业务载体验证结论

### 4.1 Web

结论：**强**

已证明事项：

- 登录、重定向、受保护路由、后台权限入口可用。
- 多角色访问控制已通过前端 E2E 验证，重点覆盖 `enterprise_user` 和 `admin`。
- 找律师、任务推进、合同审查、文档 AI 分析四条业务动作链路可通过前端 E2E 跑通。
- 统一文档工作台、右侧面板双模式、导航结构与主业务壳层已具备稳定验证。
- 后端 273 个测试为 Web 主业务 API 提供了很强的支撑证据。

限制：

- 大多数前端 E2E 通过 mock API / mock WebSocket 跑通，说明前端编排正确，但不等于真实依赖全链路全部通过。

### 4.2 Desktop

结论：**中**

已证明事项：

- Tauri 壳层可编译。
- 与 Web 前端共享主应用，构建与本地模式桥接具备基础可运行性。

限制：

- 本次没有执行真实桌面端交互验证。
- 只能确认壳层和编译层健康，不能确认桌面独有能力与本地模式 UX 真的闭环。

### 4.3 Mobile

结论：**中偏弱**

已证明事项：

- Expo 路由壳层、Tab 结构、基础页面可运行。
- 测试层健康，`10/10` 通过。

限制：

- `mobile/app/find-lawyer.tsx`、`mobile/app/contracts.tsx`、`mobile/app/cases.tsx` 仍以 `@mock-data FALLBACK` 为主。
- 当前移动端更多证明“壳层页面存在”，而非“真实业务已接通”。

### 4.4 Mini Program

结论：**弱**

已证明事项：

- H5 构建通过，包体在当前阈值内。
- 首页、聊天页、个人页基础结构存在。

限制：

- 首页快捷动作仍有多个占位路径，点击后直接提示“功能开发中”。
- 首页仍使用 emoji 图标与局部业务占位，不符合 Web 主设计系统与专业法务语境。
- 当前只能认定为轻量入口，不可认定为完整业务载体。

## 5. 按角色覆盖完整性结论

### 5.1 证据较强的角色

- `admin`
- `enterprise_user`

原因：

- 前端 E2E 直接覆盖。
- 后端权限 / 授权 / 功能专项均有回归。

### 5.2 证据中等的角色

- `platform_lawyer`
- `partner`

原因：

- 后端测试中存在相关授权验证。
- 但前端服务方端没有同等强度的角色流转验证。

### 5.3 证据偏弱的角色

- `org_admin`
- `dept_admin`
- `individual_user`
- `assistant` / `paralegal`

原因：

- 设计文档定义较完整。
- 代码中存在角色判断。
- 但自动化验证不足，尤其缺少角色专属前端流程和跨端验证。

## 6. 按运行模式结论

### 6.1 本地 / 混合 / 云端规则定义

结论：**业务规则有定义，实现约束不够强**

现状：

- `ModeGate` 对需要联网的功能做了显式门禁。
- `PrivacyContext` 提供了 `requestModeSwitch`。
- `SubscriptionGate` 具备全局弹窗引导。

问题：

- 原始 `setMode` 仍在上下文中公开，存在绕过订阅检查的可能。
- `requestModeSwitch` 在计费 API 失败时直接 fail-open。
- `ModeGate` 的“切换运行模式”按钮直接调用 `setMode(HYBRID)`，没有走订阅校验。
- `SubscriptionGate` 开通试用时将客户端类型硬编码为 `needer`，与双客户端计费模型不一致。

结论：

当前模式系统更像“体验层提示”，还不是“严格业务边界”。

## 7. 高优先级发现

### P0-1 双客户端分离未真正闭环

证据：

- `frontend/src/App.tsx`
- `frontend/src/components/pro/ProLayout.tsx`

表现：

- `/pro` 路由组只检查登录，不检查服务方角色。
- `ProLayout` 的导航链接多数直接跳到根路径，如 `/case-center`、`/management`、`/documents`、`/find-lawyer`，会脱离 `/pro/*` 体系。
- `/pro` 默认也跳到根路径 `/lawyer-dashboard`，不是 `/pro/dashboard`。

业务影响：

- 双客户端“独立入口、独立体验、独立边界”在实现上不成立。
- 服务方壳层和需求方主壳层会相互穿透。

### P0-2 前端权限矩阵比产品权限设计更宽

证据：

- `frontend/src/hooks/usePermission.ts`
- `docs/2026-03-26_安心法务-权限体系设计.md`

表现：

- 只有少数 feature 配置了角色矩阵。
- 未配置的 feature 默认直接放行。
- 设计文档使用 `assistant`，前端代码使用 `paralegal`，角色语义未统一。

业务影响：

- 容易出现入口越权可见、错误角色看见错误模块、前端角色表现与后端实际能力不一致。

### P0-3 模式切换可绕过订阅与业务边界

证据：

- `frontend/src/context/PrivacyContext.tsx`
- `frontend/src/components/mode/ModeGate.tsx`
- `frontend/src/components/mode/SubscriptionGate.tsx`

表现：

- `requestModeSwitch` 存在 fail-open。
- `ModeGate` 可直接切入 `HYBRID`。
- 试用开通固定按 `needer` 处理。

业务影响：

- 三态运行模式无法作为严格商业化与合规边界。

### P1-1 跨载体尚未形成统一业务产品面

证据：

- `mobile/app/find-lawyer.tsx`
- `mobile/app/contracts.tsx`
- `mobile/app/cases.tsx`
- `mini-program/src/pages/index/index.tsx`

表现：

- 移动端主要业务页仍以 mock data 为主。
- 小程序首页多个快捷入口尚未接通。
- 跨端设计系统也没有统一执行。

业务影响：

- 无法宣称“全项目已完成按载体的完整功能验证”。
- 只能说 Web 主载体基本成立，其余载体仍处于半成品验证阶段。

### P1-2 DesignDNA 有基线，但执行一致性仍不足

证据：

- `frontend/scripts/design-audit.sh`
- `frontend/src/pages/admin/AdminAudit.tsx`
- `frontend/src/components/ai-primitives/ConfidenceBadge.tsx`
- `mini-program/src/pages/index/index.tsx`

表现：

- 存在硬编码颜色、局部 emoji、直接 `lucide-react` 导入、打印模板绕开 token。
- 小程序和移动端并未真正复用 Web 主设计系统。

业务影响：

- 专业法务产品的“可信、克制、可审计”气质会在边缘模块和轻端入口被稀释。

### P1-3 性能已有明确边界回退

证据：

- `backend/tests/test_performance_benchmark.py`
- `frontend build` 产物尺寸

表现：

- 缓存写入性能基准失败。
- Web 大包明显，`three` / `livekit` / `editor` / `recharts` 体积偏重。

业务影响：

- 在弱网、低性能设备、重图谱/音视频/编辑场景下，存在明显卡顿和首屏压力风险。

## 8. 业务链路可用性结论

### 8.1 已有较强证据的链路

- 登录与认证
- 角色权限重定向
- 找律师委托链路
- 任务推进链路
- 合同审查链路
- 文档 AI 分析链路
- 统一文档工作台
- 右侧工作台 / 文档双模式

### 8.2 有中等证据但未完全闭环的链路

- 服务方端完整获客与案源经营链路
- 尽职调查真实外部数据链路
- IM / 实时通讯全链路
- 本地模式与桌面模式的真实交互闭环

### 8.3 证据不足的链路

- 小程序核心业务闭环
- 移动端真实业务闭环
- `individual_user` 的完整限额与付费分层体验
- 组织级角色在前端完整流程中的可用性

## 9. 建议整改顺序

### 第一阶段：先修边界，不先修表象

1. 收口 `Pro` 端路由与角色边界，保证 `/pro/*` 真正独立。
2. 把前端 feature/role 矩阵与权限设计文档对齐，消除默认放行。
3. 收口模式切换，只保留 `requestModeSwitch` 一条受控路径。

### 第二阶段：再补跨载体真业务

1. 移动端接真实 API，优先打通 `find-lawyer`、`cases`、`contracts`。
2. 小程序首页入口去掉“开发中”占位，至少打通一条最短咨询链路。
3. 将移动端 / 小程序纳入与 Web 相同的业务回归基线。

### 第三阶段：最后做设计与性能收口

1. 清理硬编码颜色、emoji、图标入口漂移。
2. 拆分重包，重点处理 `three`、`livekit`、`editor`、`recharts` 相关页面。
3. 针对缓存写入热点复盘实现，恢复性能基线通过。

## 10. 本轮审计的边界

本次结论基于真实代码阅读、自动化执行和构建结果，不基于主观猜测。

但也需要明确：

- 前端 E2E 里有较多 mock，因此更能证明前端编排正确，而非外部依赖全部真实可用。
- 移动端和小程序目前不能等同于 Web 主站成熟度。
- 仓库当前为脏工作区，本报告不试图区分哪些既有修改来自本轮之前的开发，仅针对当前仓库状态给出审计判断。

## 11. 最终判断

如果以“业务主站 Web 是否已进入可持续迭代阶段”来判断，答案是：**是**。

如果以“项目是否已经按角色、模式、载体、业务逻辑完成完整功能性验证”来判断，答案是：**还没有**。

当前最准确的结论应当是：

**Web 主载体基本成立，后端主业务稳定；但双客户端边界、三态模式约束、跨端真实业务接通和全端设计一致性仍需一轮系统性收口。**

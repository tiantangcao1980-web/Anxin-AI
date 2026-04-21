# 安心法务功能可用性与性能审计报告

日期：2026-04-18
审计范围：`backend`、`frontend`、`desktop`、`mobile`、`mini-program`
审计方式：代码结构检查 + 自动化验证 + 浏览器端回归抽样 + 构建与性能基线

## 0. 最新复验结论（同日更新）

在完成当天的修复与回归后，当前仓库状态已经明显优于本报告首次记录时的基线。

最新验证结果：

- `backend`: `./.venv/bin/pytest -q tests` → `273 passed`
- `frontend`: `npm run lint` → 通过
- `frontend`: `npm run test` → `3 passed`
- `frontend`: `npm run build` → 通过
- `frontend`: `npm run test:e2e` → `108 passed / 46 skipped / 0 failed`
- `mobile`: `npm test` → `10 passed`
- `desktop`: `cargo check` → 通过
- `mini-program`: `npm run build:h5` → 通过，但仍有包体偏大警告

基于这轮复验，当前更准确的判断是：

- Web 主线功能、权限入口、工作台/文档核心交互、关键浏览器回归已恢复为绿色基线。
- 后端核心回归已恢复为绿色基线。
- 移动端单测已恢复为绿色基线。
- 仍需关注的主要问题转为性能与工程治理类风险，而不再是大面积功能不可用。

## 1. 审计结论

当前仓库不满足"完整功能可用"的交付标准，也不满足"性能已完成稳定验收"的发布标准。

总体判断：

- 后端主业务能力大体存在，但认证链和智能体编排链有明确回归。
- Web 前端存在构建级阻断，说明主线功能当前不能稳定交付。
- 浏览器 E2E 不是少量 flaky，而是导航、文档工作台、模板入口、移动导航等多个业务域成片失败。
- 桌面端编译状态最好，小程序可构建但入口包偏大，移动端测试基线明显失配。

## 2. 已执行验证

### 2.1 后端

- `cd backend && ./.venv/bin/pytest -q tests`
  - 结果：`264 passed / 9 failed`
  - 用时：`48.12s`
- `cd backend && ./.venv/bin/pytest -q tests/test_performance_benchmark.py`
  - 结果：`9 passed`

### 2.2 前端 Web

- `cd frontend && npm run lint`
  - 结果：通过
- `cd frontend && npm run build`
  - 结果：失败
- `cd frontend && npm run test`
  - 结果：失败
  - 说明：Vitest 把 `e2e/*.spec.ts` 当成单测导入，测试脚本基线不稳定
- `cd frontend && npm run test:e2e`
  - 结果：真实启动 Playwright，`154` 条用例开始执行
  - 抽样观察到前 `51` 条中至少 `23` 条失败
  - 失败集中在任务/合同/文档工作台/协作/模板入口/移动导航

### 2.3 桌面端

- `cd desktop && cargo check`
  - 结果：通过

### 2.4 小程序

- `cd mini-program && npm run build:h5`
  - 结果：通过
  - 警告：入口包 `332 KiB`，超过推荐值 `244 KiB`

### 2.5 移动端

- `cd mobile && npm test`
  - 结果：失败
  - 原因：命令实际跑偏到错误的 Vite/uni 配置，并报缺少 `mobile/src/manifest.json`

## 3. 按角色与业务模式审计

### 3.1 角色体系

从代码上看，系统已经实现了基本角色与权限守卫：

- 登录态与功能守卫：`frontend/src/components/auth/ProtectedRoute.tsx`
- 管理后台守卫：`frontend/src/components/auth/AdminRoute.tsx`
- 前端功能权限矩阵：`frontend/src/hooks/usePermission.ts`
- 后端认证入口：`backend/src/api/routes/auth.py`

但从可用性角度看，角色链路目前只能判定为"结构存在"，不能判定为"完整可用"。原因如下：

- 认证链自动化回归失败，角色验证基础不稳定。
- 部分前端角色矩阵与真实导航/页面实现存在偏差。
- 多角色浏览器回归未形成稳定通过基线。

### 3.2 三态运行模式

从代码上看，运行模式门控已落地：

- 模式门控组件：`frontend/src/components/mode/ModeGate.tsx`
- 模式上下文：`frontend/src/context/PrivacyContext.tsx`
- 路由上的模式限制：`frontend/src/App.tsx`

审计判断：

- `LOCAL/HYBRID/CLOUD` 模式声明存在。
- 受限功能如找律师、尽调、即时通讯、知识图谱已接入门控。
- 但离线包下载、本地数据包就绪后再次放行、模式切换后的端到端业务闭环，没有形成完整通过证据。

## 4. 按业务域审计

### 4.1 AI 法务 / 智能对话

现状：

- 主路由存在：`/chat`
- 后端聊天与工作流路径存在：`backend/src/api/routes/chat.py`
- 前端消息与思考链已接入

风险：

- 前端构建被聊天消息类型漂移阻断。
- `useChatHistory.ts` 和 `store.ts` 对 `ThinkingStep` 的契约不一致。
- `Chat.tsx` 向 `Message` 注入 `thinkingSteps`，但当前被消费的类型未完全同步。

结论：

- 功能存在，但当前不能视为稳定可用。

### 4.2 智能协作 / 案件中心 / 合同管理

现状：

- 路由存在：`/case-center`、`/management`
- 后端接口存在：`cases.py`、`contracts.py`、`tasks.py`

证据：

- Playwright 用例 `business-actions.spec.ts` 中，任务流与合同流均失败。
- 一个直接原因是测试仍访问旧路由 `/tasks`，而应用已把该路由重定向到 `/case-center`。

结论：

- 业务域结构存在，但回归基线和真实产品信息架构已经脱节。
- 当前不能证明任务推进、合同上传审查、结果展示链路是稳定可用的。

### 4.3 智能文档 / 协作工作台

这是当前前端最大风险区。

现状：

- 主页面存在：`frontend/src/pages/DocumentWorkbench.tsx`
- 工作台壳存在：`frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx`
- 侧栏、顶部栏、状态栏、右侧面板均已实现

关键证据：

- `/documents` 相关多个用例失败，找不到"我的文档"、"文档工作台"、"打开 Markdown 示例"等入口。
- `/collaboration` 与 `/collaboration/:id` 相关用例失败，工作台未按预期进入 `collaboration` 模式。
- `useDocumentWorkspaceEntry.ts` 默认将入口模式回落到 `library`。

结论：

- 文档工作台具备实现痕迹，但导航语义、入口状态、真实控件可见性与回归预期明显错位。
- 当前不能认为"文档工作台闭环可用"。

### 4.4 智能调查 / 尽职调查 / 舆情监测

现状：

- 路由存在：`/monitoring`、`/investigation`
- 后端接口存在：`due_diligence.py`、`sentiment.py`

审计判断：

- 代码入口和模式门控已接好。
- 但缺少一条完整通过的端到端回归来证明调查流程、报告展示、结构化摘要输出稳定可用。

### 4.5 法律智库 / 知识图谱

现状：

- 路由存在：`/knowledge-base`、`/knowledge-graph`
- 后端接口存在：`knowledge.py`、`knowledge_management.py`

审计判断：

- 功能入口在代码上存在。
- 但模板视图、知识库选择器、知识库入口升级的浏览器回归已出现明显失败。

### 4.6 即时通讯 / RTC

现状：

- 路由与模块存在：`/messages`、`VoiceCall`、`VideoCall`
- 后端接口存在：`im.py`、`rtc.py`

审计判断：

- 能确认模块存在，不能确认完整可用。
- 当前没有稳定通过的端到端会话、呼叫链路证据。

## 5. 主要失败点与根因归类

### 5.1 前端构建阻断

阻断文件：

- `frontend/src/hooks/useChatHistory.ts`
- `frontend/src/lib/store.ts`
- `frontend/src/pages/Chat.tsx`
- `frontend/src/components/chat/ChatMessages.tsx`

根因：

- 聊天消息与思考链模型发生漂移，同一概念出现了多套不一致类型。

影响：

- `npm run build` 直接失败。
- Web 主线不可发布。

### 5.2 认证链自动化不稳定

失败测试：

- `backend/tests/test_auth_roles_permissions.py`
- `backend/tests/test_auth_surface_hardening.py`

直接原因：

- 仓库 `.env` 中 `CAPTCHA_ENABLED=true`
- 测试未统一隔离 CAPTCHA 开关，导致注册/登录/忘记密码类测试被环境配置污染

影响：

- 无法稳定证明注册、登录锁定、忘记密码限流是正确工作的。

### 5.3 智能体编排回归

失败测试：

- `backend/tests/test_chat_history_propagation.py`
- `backend/tests/test_workforce.py`

直接原因：

- `backend/src/agents/workforce.py` 对 `process()` 返回值进行了多余的 `await`
- 智能体数量已扩展到 `19`，但测试仍断言 `18`

影响：

- 智能体任务执行契约不稳定
- 测试基线与实现不同步

### 5.4 E2E 契约与真实产品重构脱节

表现：

- 旧路由重定向后，测试仍按旧路径和旧文案断言
- 文档工作台入口模式、按钮标签、导航标签与测试不一致
- 移动端底部导航文案与测试期望不一致

影响：

- 浏览器回归大量红灯
- 难以区分真实缺陷和陈旧测试

## 6. 性能审计

### 6.1 已验证部分

- 后端组件级性能基准通过：`test_performance_benchmark.py`
- 小程序 H5 可完成构建
- 桌面端可完成编译

### 6.2 明确风险

- 小程序入口包 `332 KiB`，高于推荐 `244 KiB`
- Web 前端因构建失败，无法给出可信的 bundle 与运行时性能结论
- 目前没有带真实 Postgres/Redis/Qdrant/Neo4j/MinIO 的端到端压测证据

### 6.3 性能结论

- 可以说"已有基础性能基线"
- 不能说"核心链路性能已验收"

## 7. 审计评级

### P0

- Web 前端构建失败
- 认证链回归不稳定
- 文档工作台与协作入口大面积回归失败

### P1

- 智能体编排契约回归
- E2E 脚本与真实路由/信息架构严重脱节
- 移动端测试基线错误

### P2

- 小程序入口包偏大
- 多端性能与真实依赖压测证据不足

## 8. 建议的修复顺序

1. 先修前端构建阻断，统一 `Message` / `ThinkingStep` 类型。
2. 隔离测试环境中的 CAPTCHA 与外部依赖，恢复认证链测试可信度。
3. 修复 `LegalWorkforce` 的执行契约与 agent 数量测试基线。
4. 重新对齐 Playwright：
   - 先更新旧路由断言
   - 再更新文档工作台/协作入口语义
   - 最后更新移动端导航预期
5. 补一轮真实依赖下的性能与端到端回归。

## 9. 当前可下的最终判断

当前项目适合进入"集中修复与重新验收"阶段，不适合直接作为"已完整验证通过"对外承诺。

更准确的状态表述应为：

- 架构与模块覆盖面广，主体实现较多
- 但近期重构后，Web 主线、认证链、文档工作台、E2E 基线存在明显断裂
- 需要先完成一轮 P0/P1 收口，才能开展真正意义上的完整功能验收

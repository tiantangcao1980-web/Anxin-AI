# 前端设计系统改造执行计划

## 目标

把当前“有 token、但实现漂移明显”的状态，收敛成一套真正可维护的前端视觉系统。执行目标不是只修几个页面，而是建立一条稳定链路：

`DESIGN.md -> token -> 基础组件 -> 页面壳层 -> 业务模块 -> 自动审计`

## 现状摘要

- 设计基础已存在：`frontend/src/index.css`、`frontend/src/lib/design-tokens.ts`、统一业务壳层、E2E 基线。
- 主要问题集中在：
  - feature 级硬编码颜色过多
  - 自定义交互组件缺少统一 `focus-visible`
  - 圆角/间距/字体权重在页面层自由扩散
  - 图谱、图表、支付、编辑器等高复杂模块各自维护视觉语言
  - 图标体系虽宣称统一到 `@/lib/icons`，但仍存在直接导入与 emoji 图标
  - 移动端首屏、认证体验、骨架与重模块存在感知质量风险
  - 中文排版与法务产品气质还没有真正收敛

## 升级范围

这次方案覆盖的不只是视觉皮肤，而是完整的 UI + UX 升级工程：

- 视觉系统：颜色、字体、边距、圆角、阴影、图标、图表
- 交互系统：按钮状态、表单反馈、焦点可见、空状态、错误态、加载态
- 流程体验：登录、聊天、工作台、图谱、支付、签约、移动端主流程
- 工程治理：资源目录、风险台账、审计脚本、代码评审规则

配套文件：
- `DESIGN.md`
- `RESOURCES.md`
- `docs/frontend-design-governance.md`
- `docs/frontend-design-risk-register.md`
- `frontend/scripts/design-audit.sh`

## 成功标准

### Phase 1 完成标准
- 新增 `DESIGN.md` 被团队视为单一设计真相源
- 任何新 UI 改动都能回答“我使用了哪个 token”
- `frontend/scripts/design-audit.sh` 可输出当前硬编码热点
- `frontend/scripts/design-cleanup-audit.sh` 可输出候选遗留页面、资源和样式热点

### Phase 2 完成标准
- 自定义按钮、菜单项、侧栏项、输入控件全部具备统一 `focus-visible`
- 登录页、聊天页、主导航页完成状态体系统一

### Phase 3 完成标准
- 支付、图谱、图表模块移除主要硬编码长期颜色
- 图形类组件接入统一扩展色板

### Phase 4 完成标准
- 页面层圆角与间距显著收敛
- `font-bold` / `tracking-wide` 在中文业务 UI 中大幅减少

### Phase 5 完成标准
- 图标体系彻底统一到 `@/lib/icons`
- emoji / text-as-icon 从运行态 UI 中移除
- 图表与图谱建立统一数据可视化视觉规范

### Phase 6 完成标准
- 登录、聊天、图谱、支付、签约、移动端主导航的 UX 明显优化
- 首屏任务可达性、反馈清晰度、空/错/加载状态达到统一标准

### Phase 7 完成标准
- UI 升级不引入新的感知性能问题
- 重点重模块的首屏体验与体积治理并行完成

## 执行顺序

### Phase 0 - 设计真相源与治理

目标：
- 固化设计决策，防止继续边写边漂

动作：
- 建立根目录 `DESIGN.md`
- 保留 `docs/design-system.md` 作为历史实现说明
- 增加 `frontend/scripts/design-audit.sh`
- 将审计命令接入 `frontend/package.json`

验收：
- 团队可以通过 `npm run audit:design` 快速看到热点

### Phase 0A - Cleanup Gate（去旧前置关卡）

目标：
- 先清理旧的、冗余的、未引用的样式、资源和代码，再做统一升级

动作：
- 建立 `docs/frontend-cleanup-baseline.md`
- 增加 `frontend/scripts/design-cleanup-audit.sh`
- 对休眠页面、孤儿资源、旧样式热点做第一轮归类：
  - `confirmed-unused`
  - `needs-migration`
  - `keep-for-now`
- 对已被新页面替代的旧入口建立删除清单

验收：
- 团队可以通过 `npm run audit:cleanup` 快速看到候选遗留项
- 后续每个 Phase 开始前，先跑 cleanup audit，再做当期改造
- 不再允许“新旧两套页面/样式/资源并存但没有明确归属”

### Phase 1 - 状态体系统一

目标：
- 所有核心交互都有一致的 default / hover / focus / disabled

优先文件：
- `frontend/src/lib/design-tokens.ts`
- `frontend/src/components/Layout.tsx`
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Chat.tsx`
- `frontend/src/components/chat/*`

动作：
- 给 `buttonStyle`、`inputStyle`、`toolbarButton` 增加统一 `focus-visible`
- 将侧栏按钮、图标按钮、聊天菜单按钮迁移到统一样式
- 统一 disabled 态文案和视觉反馈

验收：
- 键盘 Tab 浏览时所有核心按钮都有可见 ring
- 登录页、聊天页、主导航页不再出现“只有 hover、没有 focus”组件

### Phase 2 - 颜色治理

目标：
- 停止 feature 自行发明长期颜色

优先文件：
- `frontend/src/components/chat/PaymentPanel.tsx`
- `frontend/src/components/chat/KnowledgeGraphView.tsx`
- `frontend/src/components/knowledge-center/KnowledgeGraphExplorer.tsx`
- `frontend/src/components/dashboard/CaseDistribution.tsx`
- `frontend/src/pages/KnowledgeGraph.tsx`
- `frontend/src/components/editor/CollaborativeEditor.tsx`

动作：
- 定义图谱/图表扩展色板 token
- 定义支付方式识别 token，而不是直接引用品牌 hex
- 把编辑器调色盘拆分成“文档语义色 / 高亮色 / 打印色”三层

验收：
- 上述文件中的主视觉色可被 token 替换
- 品牌橙回到“主行动/主激活”单一职责

### Phase 3 - 图标系统治理

目标：
- 让整个产品真正只说一种图标语言

优先文件：
- `frontend/src/lib/icons.ts`
- `frontend/src/components/chat/PaymentPanel.tsx`
- `frontend/src/components/knowledge-center/KnowledgeGraphExplorer.tsx`
- `frontend/src/pages/Chat.tsx`

动作：
- 建立图标尺寸、状态、导入规范
- 清理业务组件中的直接 `lucide-react` 导入
- 移除 emoji 图标和 text-as-icon 场景

验收：
- 业务组件只通过 `@/lib/icons` 使用图标
- 无运行态 emoji 图标

### Phase 4 - 尺度治理

目标：
- 让页面节奏更像同一个产品，而不是多个模块拼接

优先文件群：
- `frontend/src/pages/*.tsx`
- `frontend/src/components/a2ui/**/*`
- `frontend/src/components/im/**/*`
- `frontend/src/components/dashboard/**/*`

动作：
- 收敛随机 `rounded-*`
- 收敛随机 `p-* / gap-*`
- 在常用页面引入统一 page shell / section / card 预设

验收：
- 核心页面的卡片、按钮、输入框 radius 只落在定义的 6 档范围内
- 页面主要布局节奏以 `8/12/16/20/24/32` 为主

### Phase 5 - 排版与中文界面修正

目标：
- 把“组件库默认感”拉回“专业法务感”

优先文件群：
- `frontend/src/pages/**/*.tsx`
- `frontend/src/components/**/*.tsx`

动作：
- 将中文大标题从 `font-bold` 收敛到 `500/600`
- 限制 `tracking-wide/wider` 在中文业务界面的使用
- 明确数据标签、徽章、英文序列号的例外场景

验收：
- 中文业务标题的主要字重符合 `DESIGN.md`
- 无大面积中文 `tracking-wide`

### Phase 6 - 复杂模块视觉重构

目标：
- 把最容易漂移的模块拉回统一系统

优先文件群：
- `components/knowledge-center/**/*`
- `components/chat/**/*`
- `components/editor/**/*`
- `components/dashboard/**/*`
- `pages/KnowledgeGraph.tsx`
- `pages/ComplianceCheck.tsx`

动作：
- 图谱、图表、支付、编辑器、签约工作流接入统一 token
- 抽离数据可视化扩展色板与打印态规范
- 收敛工作台、图谱、调查页面的信息层级和视觉锚点

验收：
- 高复杂模块不再自带独立视觉体系
- 图谱、图表、支付、编辑器样式与主产品一致

### Phase 7 - UX 专项优化

目标：
- 把体验问题纳入设计系统，不只停留在样式层

优先流程：
- 登录 / 注册 / 找回密码
- Chat 发送与工作台
- 文档工作台
- 图谱探索
- 支付 / 签约
- 移动端导航与输入

动作：
- 优化首屏可达性
- 统一加载、空状态、错误状态
- 清晰化步骤反馈、系统状态、风险提示
- 做移动端单手可达和首屏优先级整理

验收：
- 主流程每一步都清楚“现在在哪、下一步是什么、失败了怎么办”
- 移动端主任务首屏可操作

### Phase 8 - 视觉性能与稳定性

目标：
- 避免 UI 升级把首屏和重模块做得更慢

动作：
- 对图谱、编辑器、three.js、livekit、recharts 模块做懒加载与体验治理
- 收敛骨架屏侵入性，避免长时间“像坏掉”
- 将视觉优化与 bundle 风险一并审查

验收：
- 重点模块的首屏反馈更稳定
- 不新增显著 chunk 警告与感知白屏

## 执行方式

每一阶段都按同一节奏推进：

1. 更新 token 或设计规范
2. 先改基础组件和壳层
3. 再改业务模块
4. 跑 `npm run audit:design`
5. 跑 `npm run audit:cleanup`
6. 跑 `npm run test:e2e -- auth.spec.ts --project=chromium`
7. 跑 `npm run test:e2e -- ui-regression.spec.ts --project=chromium`
8. 在高复杂模块迭代后补运行针对性页面截图或视觉核查

## 风险控制

- 不引入新依赖
- 每次只推进一个设计系统主题，避免颜色、状态、布局一起混改
- 不直接追求全仓一次性“完美视觉统一”，优先修高频路径
- 风险明细见 `docs/frontend-design-risk-register.md`
- 清理基线见 `docs/frontend-cleanup-baseline.md`
- 若后续需要引入 Fontsource、图标自动化或字体子集化，单独申请批准

## 推荐最近两次迭代

### Iteration A
- Phase 1
- 目标页面：`/login`、`/chat`、主导航、左侧栏

### Iteration B
- Phase 2
- 目标页面：知识图谱、支付面板、图表组件、编辑器导出样式

### Iteration C
- Phase 3 + Phase 5
- 目标页面：图标统一、中文排版、标签与标题体系

### Iteration D
- Phase 6 + Phase 7
- 目标页面：图谱探索、签约、支付、移动端主流程

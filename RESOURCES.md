# 安心 AI 法务 Design Resources

> 本文件是 `DESIGN.md` 的资源配套目录，定义全项目在图标、字体、动效、图表和视觉素材上的唯一选择，避免后续 UI/UX 改造继续漂移。

## 1. Icon Library

### Primary Choice
- Library: `lucide-react`
- Import policy: 统一通过 `frontend/src/lib/icons.ts`
- Reason:
  - 已广泛落地
  - 线性风格适合法务产品的克制与专业感
  - Tree-shaking 友好
  - 易于统一尺寸与状态

### Disallowed
- 业务组件直接从 `lucide-react` 导入
- 在 UI 中新增 `@heroicons/react` 用法
- emoji / Unicode / text-as-icon

### Current Debt
- `frontend/src/components/chat/PaymentPanel.tsx` 直接从 `lucide-react` 导入
- `frontend/src/components/knowledge-center/KnowledgeGraphExplorer.tsx` 用 emoji 表示节点类型
- `frontend/src/pages/Chat.tsx` 使用 `💡` 作为 toast 图标

## 2. Typography

### Current Stack
- `"Inter", "PingFang SC", "Microsoft YaHei UI", "Noto Sans SC", system-ui, sans-serif`
- Monospace: `"JetBrains Mono", "SF Mono", "Fira Code", Consolas, monospace`

### Policy
- 在未获准引入新依赖前，不新增 Fontsource 包。
- 中文业务 UI 优先使用当前栈，不切换到新的展示字体。
- 打印 / 导出文档可使用宋体系衬线字体，但运行态界面不使用。

### Current Debt
- 中文页面 `font-bold` 过多
- 多处 `tracking-wide / tracking-wider / tracking-[...]` 用在中文业务标签
- 验证码输入场景以外，`font-mono` 应收敛

## 3. Spacing & Radius

### Approved Scale
- Spacing: `4 / 8 / 12 / 16 / 20 / 24 / 32`
- Radius: `4 / 8 / 12 / 16 / 24 / full`

### Disallowed
- `rounded-3xl` 作为常规业务卡片默认值
- 随机 `shadow-[...]`
- 随机 `5px`、`9px`、`14px` 等非标准业务间距

### Current Debt
- `rounded-lg` / `rounded-xl` / `rounded-2xl` / `rounded-3xl` 混用范围过大
- 页面里存在自定义 shadow 和半档 spacing

## 4. Motion

### Allowed Motion
- hover 提示
- 折叠展开
- 面板切换
- 成功反馈
- 骨架与加载

### Disallowed Motion
- 与任务无关的持续脉冲
- 基础容器漂浮感动画
- 仅为“AI 感”而加入的夸张动效

## 5. Data Viz & Graphs

### Policy
- 图表色板和图谱节点色必须来自统一语义扩展 token。
- 不允许组件内部长期维护一份 hex 彩虹表。
- 图表 tooltip、legend、background 都要接入 surface 和 text token。

### Current Debt
- `KnowledgeGraphExplorer`
- `KnowledgeGraphView`
- `CaseDistribution`
- `AdminEnterprise`
- `ComplianceCheck`

## 6. Payments & Third-Party Brands

### Policy
- 第三方品牌识别色可以保留，但必须通过语义 token 或品牌映射层使用。
- 品牌 logo 本体允许保留官方色，不应扩散到按钮边框、hover、背景系统。

### Current Debt
- 微信 / 支付宝支付按钮仍以硬编码色直写实现
- 登录页第三方按钮仍内嵌品牌 fill

## 7. UX Upgrade Focus

### Highest Priority Journeys
- 登录 / 注册 / 找回密码
- Chat 主工作流
- 文档工作台
- 智能调查 / 图谱
- 支付与签约
- 移动端主导航与输入区

### UX Goals
- 首屏更快进入任务
- 用户始终知道当前状态、下一步和风险级别
- 桌面端主次区分清晰，移动端单手可用
- 信息更易扫描，操作更可预期

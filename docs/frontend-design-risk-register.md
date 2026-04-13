# 前端 UI/UX 风险台账

## 使用方式

- 这是执行计划的配套风险清单。
- 每次设计系统改造前，先确认本次迭代覆盖了哪些风险项。
- 风险状态建议使用：`open / in_progress / mitigated / accepted`

## 风险矩阵

| ID | 类别 | 当前症状 | 代表文件 | 影响 | 建议动作 | 状态 |
|---|---|---|---|---|---|---|
| R0 | 新旧混同 | 旧页面、旧样式、旧资源未清理，后续升级可能双轨并存 | `pages/News.tsx`（保留项）, 样式与资源层遗留热点 | 执行不彻底，团队误用旧实现 | 建立 Cleanup Gate，先盘点再删除/迁移 | in_progress |
| R1 | 图标体系 | 存在 emoji 图标、直接库导入、图标状态不统一 | `components/knowledge-center/KnowledgeGraphExplorer.tsx`, `components/chat/PaymentPanel.tsx`, `pages/Chat.tsx` | 视觉语言分裂，专业感下降 | 统一到 `@/lib/icons` 与图标状态规范 | open |
| R2 | 颜色纪律 | feature 级硬编码颜色多，品牌橙职责外溢 | `pages/KnowledgeGraph.tsx`, `components/chat/PaymentPanel.tsx`, `components/dashboard/CaseDistribution.tsx` | 品牌识别稀释、暗色模式难维护 | 定义扩展色板 token 并替换长期 hex | open |
| R3 | 交互状态 | 自定义按钮 focus-visible 缺失 | `components/Layout.tsx`, `pages/Login.tsx`, `pages/Chat.tsx` | 键盘可达性差，交互确定感不足 | 收敛到统一按钮/输入/菜单态 | open |
| R4 | 字体权重 | 中文业务 UI 大量 `font-bold` | `pages/*`, `components/chat/*`, `components/knowledge-center/*` | 信息层级粗糙，法务气质不稳 | 收敛到 500/600 层级 | open |
| R5 | 字距问题 | 中文界面使用 `tracking-wide` 和自定义 tracking | `components/chat/SigningWorkflow.tsx`, `components/knowledge-center/*`, `pages/CaseDetail.tsx` | 可读性下降，组件库味过重 | 仅保留英文小标签例外 | open |
| R6 | 间距体系 | 存在大量非标准 spacing | 全仓页面与组件 | 页面节奏不统一 | 统一 spacing token 与 shell 预设 | open |
| R7 | 圆角体系 | `rounded-lg/xl/2xl/3xl/full` 扩散 | `components/a2ui/*`, `components/chat/*`, `pages/*` | 模块像多个产品拼接 | 收敛到 6 档 radius | open |
| R8 | 阴影体系 | 存在自定义 `shadow-[...]` 与多套局部 shadow 逻辑 | `pages/Chat.tsx`, `components/*` | 立体层级不统一 | 统一 elevation token | open |
| R9 | 图谱/图表视觉 | 图谱、图表、legend 自成体系 | `KnowledgeGraphExplorer`, `KnowledgeGraphView`, `CaseDistribution`, `AdminEnterprise` | 高复杂模块风格割裂 | 建立数据可视化视觉规范 | open |
| R10 | 打印/导出 | 文档导出样式与主应用完全断裂 | `components/editor/CollaborativeEditor.tsx`, `components/chat/CanvasEditor.tsx` | 产品感断层，输出不一致 | 建立“运行态/打印态”双规范 | open |
| R11 | 登录与认证 UX | 左右分栏在不同端表现不稳定，骨架/白屏风险暴露 | `pages/Login.tsx`, `PageSkeleton.tsx` | 首屏可信度下降 | 收敛认证首屏、弱化骨架侵入性 | open |
| R12 | 移动端 UX | 首屏骨架、输入区、底部导航优先级可能冲突 | `components/mobile/*`, `pages/Chat.tsx` | 主任务不可达，单手使用差 | 专项移动端可达性迭代 | open |
| R13 | 信息架构 | 页面内强调方式过多，卡片层级不稳定 | chat / knowledge / due diligence | 扫描成本高 | 统一标题、辅助文字、元信息规则 | open |
| R14 | 组件复用 | 同一功能出现第二套按钮或状态徽章样式 | `pages/*` + `components/*` | 维护成本升高 | 基础组件回收并替换页面级私有样式 | open |
| R15 | 可访问性 | focus、对比度、点击区、状态提示未系统验证 | 全仓 | 无障碍与可用性风险 | 在每个 phase 增加 a11y 验收 | open |
| R16 | 视觉性能 | chunk 大、骨架与重型模块抢首屏 | `KnowledgeGraph`, `Chat`, `DueDiligence` | 影响感知速度与稳定性 | 把 UI 升级与性能治理并行推进 | open |

## 补充说明

### 最高优先级组合
- R0 新旧混同
- R1 图标体系
- R2 颜色纪律
- R3 交互状态
- R11 登录与认证 UX
- R12 移动端 UX

### 第二优先级组合
- R4 字体权重
- R5 字距问题
- R6 间距体系
- R7 圆角体系
- R8 阴影体系

### 高复杂模块专项
- R9 图谱/图表视觉
- R10 打印/导出
- R16 视觉性能

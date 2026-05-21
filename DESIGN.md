# 安心智能助手 DESIGN.md

> 单一设计真相源。`docs/design-system.md` 保留实现说明与历史背景；当两者冲突时，以本文件为准。
> 适用范围：`frontend/` Web 主界面优先，随后同步到 `mobile/` 与 `mini-program/`。

## 1. Visual Theme & Atmosphere

安心智能助手的界面不是通用 SaaS 控制台，也不是刻意强调“AI 感”的炫技产品。它应该像一间被精心整理过的专业法律工作室：光线柔和、秩序清晰、层级克制，始终把判断、风险和证据放在视觉优先级的前面。品牌气质要传达“可信赖的专业协作伙伴”，而不是“高刺激的技术平台”。这意味着页面需要保留足够的留白和呼吸感，但不能松散；要有明显的结构边界，但不能显得刻板或官僚；要让用户感受到系统正在高效工作，但不能用过量动画和色彩制造噪声。

整体视觉语言采用“暖灰基底 + 琥珀橙品牌强调 + 克制的 AI 辅助色”体系。暖灰而非纯黑，让文本与面板更适合法务长时阅读；琥珀橙承担主行动、关键进度与品牌识别，不再扩散到图谱、图表、支付等所有模块；AI 紫只用于 AI 身份与生成态提示，不参与普通业务流程。界面密度以“桌面端中等偏紧凑、移动端舒展”为原则，优先保障扫描效率。标题语气要稳，正文要耐读，交互反馈要明确但不过度兴奋。

这个系统的核心设计哲学是：**让复杂法律工作看起来有秩序、可追踪、可协作，并且始终比 AI 更像专业人士。**

## 2. Color Palette & Roles

### Primary & Brand
- **Brand / Primary 500** (`hsl(25 95% 53%)`): `--primary`，主按钮、主行动、激活状态、关键进度。
- **Primary 600** (`hsl(21 90% 48%)`): `--primary-600`，主按钮 hover / pressed。
- **Primary 100** (`hsl(34 100% 92%)`): `--primary-100`，选中底色、浅强调底。
- **Primary 50** (`hsl(33 100% 97%)`): `--primary-50`，轻提示背景、空状态强调。

### Secondary & Accent
- **Secondary Surface** (`hsl(30 14% 96%)`): `--secondary`，次级面板和分组背景。
- **Accent Surface** (`hsl(35 100% 96%)`): `--accent`，轻交互 hover 面。
- **AI Accent** (`hsl(262 83% 58%)`): `--ai`，仅用于 AI 身份、推理、流式生成态。
- **AI Surface** (`hsl(262 60% 97%)`): `--ai-surface`，AI 辅助卡片或标签的低强度底色。

### Text Scale
- **Text Primary** (`hsl(20 14% 10%)`): `--foreground`，正文、标题、主要数据。禁止用纯 `#000000` 替代。
- **Text Secondary** (`hsl(20 9% 46%)`): `--muted-foreground`，说明文、辅助描述、次级元信息。
- **Text Tertiary** (`hsl(20 8% 60%)`): 新增 `--text-tertiary`，时间戳、弱标签、边缘说明。
- **Text Disabled** (`hsl(20 7% 72%)`): 新增 `--text-disabled`，禁用控件与不可操作文案。

### Surface & Background
- **Page Background** (`hsl(0 0% 100%)`): `--background`，页面底层。
- **Surface 1** (`hsl(0 0% 100%)`): `--surface-1`，一级卡片、输入容器。
- **Surface 2** (`hsl(30 14% 98%)`): `--surface-2`，二级卡片、hover 面、筛选条。
- **Surface 3** (`hsl(32 18% 95%)`): `--surface-3`，分组底、图表辅助面。
- **Dark Background** (`hsl(20 16% 8%)`): `.dark --background`，深色模式底层。
- **Dark Surface 1** (`hsl(20 15% 11%)`): `.dark --surface-1`，深色主卡片。
- **Dark Surface 2** (`hsl(20 14% 14%)`): `.dark --surface-2`，深色次级层。

### Interactive States
- **Default**: 使用语义 token，不允许硬编码品牌色。
- **Hover**: 亮色模式优先使用 `surface-2` 或 `primary/5`；深色模式使用亮度提升而非饱和提升。
- **Focus Ring** (`0 0 0 3px hsl(25 95% 53% / 0.18)`): 全局键盘焦点环，所有自定义按钮、切换、菜单项必须可见。
- **Active / Pressed**: 使用 `--primary-600` 或轻微缩放，不用额外新颜色。
- **Disabled**: 统一 `opacity` + `text-disabled` + `pointer-events-none` 语义，不只降低透明度。

### Borders & Dividers
- **Border Primary** (`hsl(30 13% 91%)`): `--border`，标准边框。
- **Border Strong** (`hsl(30 12% 84%)`): 新增 `--border-strong`，选中或高对比边框。
- **Border Subtle** (`hsl(30 10% 94%)`): 新增 `--border-subtle`，分割线与弱容器。
- **Focus Border**: 主交互元素聚焦时边框应向 `--primary` 靠拢，但不覆盖焦点环。

### Semantic
- **Success** (`hsl(142 76% 36%)`): `--success`，通过、完成、健康状态。
- **Warning** (`hsl(38 92% 50%)`): `--warning`，提醒、待处理、中风险。
- **Destructive** (`hsl(0 72% 51%)`): `--destructive`，错误、高风险、危险操作。
- **Info** (`hsl(217 91% 60%)`): `--info`，链接、信息提示、非主品牌数据。

### Shadows
- **Shadow Card** (`0 8px 24px rgba(15, 23, 42, 0.06)`): `--shadow-card`，标准卡片。
- **Shadow Float** (`0 18px 48px rgba(15, 23, 42, 0.12)`): `--shadow-float`，悬浮层、弹层。
- **Shadow Focus** (`0 0 0 3px hsl(25 95% 53% / 0.35)`): `--shadow-focus`，仅用于焦点，不用于 hover 装饰。

## 3. Typography Rules

### Font Families
- **Primary Sans**: `"Inter", "PingFang SC", "Microsoft YaHei UI", "Noto Sans SC", system-ui, sans-serif`
- **Secondary Serif**: `"Source Han Serif SC", "Songti SC", "STSong", serif`，仅用于打印文档或正式文书预览。
- **Monospace**: `"JetBrains Mono", "SF Mono", "Fira Code", Consolas, monospace`

### Hierarchy Table

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | Primary Sans | 40px | 500 | 1.2 | -0.03em | 仅首页/品牌展示 |
| Page Title | Primary Sans | 32px | 500 | 1.25 | -0.02em | 一级页面标题 |
| Section Title | Primary Sans | 24px | 500 | 1.3 | -0.01em | 区块标题 |
| Panel Title | Primary Sans | 20px | 500 | 1.35 | -0.01em | 卡片/面板标题 |
| Lead Body | Primary Sans | 16px | 400 | 1.75 | 0 | 长文本、AI 回复 |
| Body | Primary Sans | 14px | 400 | 1.65 | 0 | 标准正文 |
| Small Body | Primary Sans | 13px | 400 | 1.6 | 0 | 表格、说明 |
| Caption | Primary Sans | 12px | 400 | 1.5 | 0.01em | 时间戳、弱标签 |
| Data Emphasis | Primary Sans | 14px | 500 | 1.5 | 0 | 指标和数值 |
| Code / Token | Monospace | 12px | 500 | 1.5 | 0 | 标识符、命令、日志 |

### Typography Principles
- 中文界面标题默认使用 `500`，避免 `700` 带来的压迫感；只有数据徽章或极小数值标签可使用 `600`。
- 正文、说明和表单标签一律不加宽 tracking；`tracking-wide/wider` 仅允许出现在全英文、超小标签、序列号类场景。
- 大标题必须使用轻微负字距；14px 及以下正文不允许负字距。
- 文书打印与导出可切换到衬线字体，但应用运行态 UI 不使用宋体类字体。

## 4. Component Stylings

### Buttons

**Primary Button (Main CTA)**
- Background: `hsl(var(--primary))`
- Text: `hsl(var(--primary-foreground))`
- Padding: `12px 16px`
- Radius: `16px`
- Border/Shadow: 无边框，`shadow-sm`
- Hover: `bg-primary-600`，允许 `-1px` 轻微上浮
- Focus: `focus-visible:ring-[3px]` + `ring-primary/20`
- Disabled: `text-disabled` + `opacity-50` + `pointer-events-none`
- Use: 提交、确认、开始执行

**Secondary Button (Support Action)**
- Background: `surface-1`
- Text: `foreground`
- Border: `1px solid border`
- Hover: `surface-2`
- Focus: 与主按钮一致
- Use: 次要流程、取消、切换视图

**Ghost / Icon Button**
- Background: transparent
- Text: `muted-foreground`
- Hover: `surface-2`
- Focus: 必须有 ring，不允许只有颜色变化
- Use: 工具栏、列表操作、输入区附件按钮

### Cards & Containers

**Standard Card**
- Background: `surface-1`
- Padding: `20px`
- Radius: `24px`
- Border: `border/70`
- Shadow: `shadow-card`
- Use: 工作台卡片、表单卡片、统计卡片

**Subtle Container**
- Background: `surface-2`
- Padding: `16px`
- Radius: `16px`
- Border: optional `border-subtle`
- Shadow: none
- Use: 筛选器、嵌套分组、空状态承载

**Floating Panel**
- Background: `surface-1`
- Radius: `24px`
- Border: `border`
- Shadow: `shadow-float`
- Use: 下拉菜单、右键菜单、弹出工作台

### Input Fields

**Text Input / Textarea**
- Background: `surface-1`
- Text: `foreground`
- Placeholder: `muted-foreground`
- Border: `border`
- Radius: `16px`
- Default Height: `44px` minimum
- Focus: `primary` 边框 + 3px ring
- Disabled: `surface-2` + `text-disabled`
- Use: 登录表单、搜索框、对话输入区

**Search Input**
- Left icon fixed at 16px
- Background: `surface-1`
- Border: `border/70`
- Hover: `surface-2`
- Focus: ring 与搜索按钮联动

### Navigation

**Top Navigation**
- Height: `56-60px`
- Background: `background/95` + blur
- Border bottom: `border-subtle`
- Active module: 使用主色下划线或浅底，不用高饱和胶囊

**Sidebar Item**
- Default: `muted-foreground`
- Active: `primary/10` 背景 + `primary` 文本
- Hover: `muted`
- Focus: 可见 ring
- Minimum height: `40px`

### Images & Media
- 业务 UI 中避免装饰性大插图抢主视觉；优先使用图标、数据、结构。
- 截图、合同预览、图谱画布应使用统一浅色/深色容器背景，不允许每个模块自定义一套底色。
- 图表与图谱颜色必须来自语义扩展色板，不允许页面局部自行发明色系。

### Distinctive Components

**Chat Bubble**
- User: `primary` 底，`rounded-2xl rounded-br-md`
- Assistant: `surface-1` + `border`
- AI 状态条: 使用 `ai` 语义色，不混入业务成功/危险色

**Workbench Panel**
- 使用 `surface-1 + shadow-card + border/70`
- Header 固定使用 `Panel Title` 规格
- 工具按钮进入统一 `Ghost / Icon Button` 体系

**Graph Node / Chart Legend**
- 节点、图例、数据系列必须映射到统一扩展 token：`entity`, `law`, `document`, `conclusion`, `query`
- 禁止在组件内部直接写 hex 作为长期设计值

### Icon System

**Primary Icon Library**
- 全站唯一图标库：`lucide-react`
- 导入入口：`@/lib/icons`
- 禁止在业务组件中直接 `import { X } from 'lucide-react'`
- 禁止在运行态 UI 使用 emoji、Unicode 符号或文本字符代替图标

**Icon Size Variants**
- `xs` 12px: 状态点、微标签
- `sm` 16px: 文本行内、表单前缀
- `md` 20px: 导航、按钮、列表主图标
- `lg` 24px: 模块标题、空状态辅助
- `xl` 32px: 空状态、引导卡片

**Icon States**
- Default: `muted-foreground`
- Hover: `foreground`
- Active / Selected: `primary`
- Disabled: `text-disabled` + `opacity-50`
- Success / Warning / Error: 只允许使用语义色，不允许额外自定义品牌色

**Icon Rules**
- 同一个页面不要混用线性风格和填充风格的主图标
- 图标按钮最小点击区域 44px
- 图标与文本默认间距 8px，小型紧凑按钮可降为 6px

## 5. Layout Principles

### Spacing Scale
- 基准采用 **4px 网格**，但页面主体节奏以 `8/12/16/20/24/32` 为常用阶梯。
- 标准卡片内边距：`20px`
- 模块间距：`24px`
- 控件间距：`8px / 12px`
- 对话消息组间距：`24px`

### Radius Scale
- `4px`: 小徽章、细小标签
- `8px`: 表格小控件
- `12px`: 紧凑输入、列表子项
- `16px`: 标准按钮、输入框、标签组
- `24px`: 卡片、面板、抽屉
- `9999px`: 头像、胶囊按钮

### Grid & Breakpoints
- Mobile: `<768px`
- Tablet: `768px - 1023px`
- Desktop: `>=1024px`
- Desktop 业务页优先采用 `page shell + header + content sections`，避免自由拼贴式布局。

### Density Rules
- 法务正文、合同预览、报告页以可读性优先，行长不要超过 `72-80` 字符。
- 仪表盘、工作台允许更高信息密度，但所有块状区域必须有对齐的顶边和统一卡片节奏。
- 任何页面都不应同时出现超过 3 个视觉主层级；卡片嵌套最多两层。
- 标题、过滤器、操作条、内容区之间必须遵守稳定的 `12/16/24` 节奏，不允许为补视觉随意插入 `5px`、`9px`、`14px` 之类间距。

## 6. Depth & Elevation

### Shadow Philosophy
- 亮色模式采用柔和暖灰阴影，不使用冰冷蓝紫投影。
- 深色模式优先使用“边框 + 轻深影”的双层深度，不堆叠发光感。
- Hover 的主变化优先是边框与轻微位移，其次才是阴影。

### Elevation Levels
- **Level 0**: 页面底层，无遮罩无阴影。
- **Level 1**: 普通卡片，`shadow-card`
- **Level 2**: 下拉/浮层，`shadow-float`
- **Level 3**: 全局弹窗/抽屉，`shadow-float` + blur backdrop

### Motion
- Hover: `150ms`
- Expand / Collapse: `250ms`
- Route / Panel Transition: `250-400ms`
- 不允许对基础页面容器使用持续脉冲、漂浮或夸张缩放动画。
- 微交互动效只服务状态变化、层级切换、成功反馈；不用于“制造 AI 感”。
- 骨架屏与加载动画优先使用中性占位，不允许抢走页面首要视觉。

## 7. Do's and Don'ts

### Do
- 使用语义 token，而不是直接写颜色。
- 让焦点态和禁用态与 hover 一样明确。
- 让中文标题保持稳重，优先 `500` 字重。
- 在图表、图谱、支付、AI 状态等高变化区域，先定义语义扩展色板再编码。
- 把新页面接入统一 page shell / surface card / header 语义。
- 只通过 `@/lib/icons` 使用 Lucide 图标。
- 用统一标题层级和 spacing token 组织信息，而不是靠粗体和彩色硬堆重点。
- 在移动端优先保证主流程单手可达和首屏可操作。

### Don’t
- 不要在业务页面直接写 `#07C160`、`#1677FF`、`#3b82f6` 这类长期样式色。
- 不要让每个模块发明自己的底色、圆角和阴影。
- 不要在中文 UI 上广泛使用 `font-bold` 和 `tracking-wide`。
- 不要只做 hover，不做 `focus-visible`。
- 不要把品牌橙同时当作成功色、图表色、支付色、边框色、背景色一起用。
- 不要在 UI 中用 emoji 当图标，尤其不能出现在图谱、导航、状态提示和 toast 主视觉里。
- 不要在页面中直接导入第二套图标库。
- 不要为了局部”好看”引入自定义 `shadow-[...]` 或随机尺寸间距。
- 不要用 `text-emerald-*` / `text-green-*` 表示成功状态，统一用 `text-success`。
- 不要用 `text-amber-*` / `text-yellow-*` 表示警告状态，统一用 `text-warning`。
- 不要用 `text-red-*` 表示错误状态，统一用 `text-destructive`。

## 8. Responsive Behavior

### Mobile
- 单栏优先，底部导航承担主路由切换。
- 主要 CTA 高度不低于 `44px`
- 输入区、筛选区、顶部导航要避免双层堆叠导致首屏挤压。
- 大卡片在移动端缩到 `16px` radius 和 `16px` padding。
- 移动端首屏必须优先显示主任务，而不是骨架、说明、装饰。
- 底部输入区、底部导航和安全区之间不能互相遮挡。

### Tablet
- 允许双栏，但侧栏必须可收起。
- 图谱、工作台、聊天右栏应优先保留主内容，次内容折叠到抽屉。

### Desktop
- 三栏布局允许，但视觉锚点只能有一个主面和一个辅面，避免左右同权抢焦点。
- 复杂工作区需要清晰 header、toolbar、content 分层。

## 9. Agent Prompt Guide

### Tokens To Reuse First
- Colors: `--primary`, `--primary-600`, `--surface-1`, `--surface-2`, `--foreground`, `--muted-foreground`, `--success`, `--warning`, `--destructive`, `--info`, `--ai`
- Radius: `16px`, `24px`, `9999px`
- Shadows: `--shadow-card`, `--shadow-float`
- Typography: Page Title `32/500/-0.02em`, Section Title `24/500/-0.01em`, Body `14/400/1.65`
- Icons: `@/lib/icons` only, default sizes `16 / 20 / 24`

### Example Prompts
- “基于 `DESIGN.md` 为 `frontend/src/pages/Contracts.tsx` 收敛为统一 page shell，禁止新增硬编码颜色。”
- “把 `PaymentPanel` 重构到语义色板，保留微信/支付宝识别，但不直接写品牌 hex。”
- “统一 `KnowledgeGraphExplorer` 和 `KnowledgeGraphView` 的节点色与焦点态，改用设计 token。”
- “清理中文页面中的 `font-bold`、`tracking-wide` 和随机 `rounded-*`，收敛到 DESIGN.md 规定的排版与尺度。”
- “把直接从 `lucide-react` 导入或使用 emoji 图标的组件，迁移到 `@/lib/icons` 与统一图标状态体系。”

### Iteration Checklist
- 这个颜色能映射到哪个 token？
- 这个按钮是否同时有 default / hover / focus / disabled？
- 这个模块是否复用了统一卡片、标题、输入和工具按钮体系？
- 这个改动会不会让品牌橙承担第二种语义？
- 这个图标是否来自唯一图标库？
- 这个标题是否真的需要 `font-bold`？
- 这个间距和圆角是否落在定义尺度内？

## 10. 飞书 / 企业微信参照规范（2026-05-22 新增）

> 自 [产品蓝图 2026-05-22](docs/plans/2026-05-22-product-blueprint.md) 起，安心智能助手的产品形态对标"飞书 / 企业微信"：桌面 + 移动是主入口，Web 仅作官网与后台。本节定义对标后的视觉细则，与本文件第 1-9 节并存（冲突以本节为准）。

### 10.1 双品牌色策略

| 角色 | Token | 用途 |
|---|---|---|
| Brand（琥珀橙） | `--primary` = `hsl(25 95% 53%)` | 品牌身份、关键 CTA、激活态、品牌徽章 |
| IM Blue（飞书蓝） | `--im-primary` = `hsl(217 100% 55%)`（`#1664FF`） | 消息高亮、@ 提及、链接、信息提示、在线状态描边 |
| Neutral（中性灰） | `--surface-*` `--border-*` | 工作台基底，淡化品牌噪声 |

> **关键原则**：橙色是"品牌锚"，蓝色是"沟通锚"。聊天气泡、链接、@提及用蓝；按钮 CTA、激活模块、品牌徽章用橙。**不能让橙色承担信息蓝的语义**。

### 10.2 三栏桌面布局（飞书风）

```
┌─ 左导航条 56px ─┬─ 中列表 280-320px ─┬─ 右内容 自适应 ─────────┐
│ avatar 32px    │ 列表标题            │ 顶部 chrome 8px       │
│ ───            │ 搜索 32px           │ 工具栏 40px            │
│ 消息    📩     │ ─── 12px            │ ─────                  │
│ 任务    ✅     │ 列表项 64-72px      │ 内容（artifact-first）  │
│ 工作台  🧰     │   ├ avatar 36       │                        │
│ 知识    📚     │   ├ 标题 14/500     │                        │
│ ─── flex-1    │   ├ 摘要 12/400     │                        │
│ 设置    ⚙️     │   └ 时间 12/400     │                        │
│ avatar 28px    │                    │                        │
└────────────────┴────────────────────┴─────────────────────────┘
       │ 状态栏 24px ─ 模式 · 同步 · 在线 · ⌘K 命令面板          │
```

**关键尺寸**：

| 元素 | 飞书 | 企微 | 我们 |
|---|---|---|---|
| 左导航条宽 | 64 | 56 | **56px** |
| 中列表宽 | 280-320 | 260-300 | **280px**（可拖拽 240-360） |
| 顶部 chrome | 28（macOS）/ 32（Windows） | 同 | **同（系统原生）** |
| 工具栏 | 40 | 40 | **40px** |
| 状态栏 | 24 | 22 | **24px** |
| 列表项 | 64-72 | 56-64 | **64px** |
| 头像 | 32/36/40 | 32/36 | **32/36/40** |

### 10.3 移动 4 tab 规范

| Tab | 图标（lucide） | 标签 | 路由 |
|---|---|---|---|
| 消息 | `MessageSquare` | 消息 | `(tabs)/messages` |
| 任务 | `ListChecks` | 任务 | `(tabs)/tasks` |
| 工作台 | `LayoutGrid` | 工作台 | `(tabs)/workbench` |
| 我 | `User` | 我 | `(tabs)/me` |

**尺寸**：
- Tab 高 56 + safe-area
- Tab 图标 24px，激活态描边 + brand 色
- 标签字号 11/500，激活 brand，未激活 `text-muted`
- 列表项最小高 64px，触控点不小于 44px

### 10.4 圆角阶梯（飞书风：克制）

原 DESIGN.md 默认大圆角（16/24px）偏"消费 App"。对标飞书后改：

| 用途 | 原 token | 新 token | 说明 |
|---|---|---|---|
| 标签 / 徽章 | `--radius-subtle` 4px | **4px** 不变 | |
| 表格 / 紧凑控件 | `--radius-sm` 6px | **6px** 不变 | |
| 标准按钮 / 输入框 | `--radius-md` 8px | **8px**（原 16px → 8px） | 与飞书一致 |
| 卡片 / 面板 | `--radius-xl` 16px | **12px**（原 24px → 12px） | 卡片不要太圆 |
| 抽屉 / 弹层 | `--radius-2xl` 20px | **16px**（原 24px → 16px） | |
| 头像 / 胶囊 | `--radius-pill` 9999px | **9999px** 不变 | |

> **过渡策略**：DESIGN.md 第 5.2 节"Radius Scale"保持表述；实施时只调 `tailwind.config.js` 和 token css 变量，业务组件不需改类名。

### 10.5 列表项规范（飞书风：扁平 + 高密度）

会话/任务/通知列表项统一结构：

```tsx
<li className="flex items-start gap-3 px-4 py-3 hover:bg-surface-2">
  <Avatar size={36} />
  <div className="flex-1 min-w-0">
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium truncate">{title}</span>
      <time className="text-xs text-muted-foreground">{time}</time>
    </div>
    <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">{preview}</p>
  </div>
  {unread > 0 && <Badge>{unread}</Badge>}
</li>
```

**约束**：
- 不允许在列表项加阴影；hover 用 `--surface-2`，激活用 `--primary/10`；
- 头像永远圆形；
- 未读徽章使用 `--im-primary`（蓝），不用品牌橙；
- 时间戳 `--text-tertiary`，不用 `--muted-foreground`（避免与摘要同色）。

### 10.6 聊天气泡规范（飞书风）

| 角色 | 背景 | 文字 | 圆角 |
|---|---|---|---|
| 我（发送方） | `--im-primary`（飞书蓝） | white | `rounded-2xl rounded-br-md` |
| 对方 / Agent | `--surface-1` + `border` | `--foreground` | `rounded-2xl rounded-bl-md` |
| 系统 | `--surface-2` + 居中 | `--muted-foreground` | `rounded-md` |
| Artifact 引用 | `--surface-1` + `--border-strong` + 左边 4px brand 色条 | `--foreground` | `rounded-md` |
| AI 思考态 | `--ai-surface` | `--ai` | `rounded-2xl` |

> 原 DESIGN.md 第 4 节定义"User 用 primary 底"。本节改为**用 IM 蓝**：避免聊天界面被品牌橙占据，与飞书 / 企微视觉对齐。品牌橙保留给 CTA / 激活态。

### 10.7 命令面板（Cmd+K）

参照飞书 `⌘K` / VS Code `⌘P`：

- 触发：桌面 `⌘K`（macOS） / `Ctrl+K`（Windows/Linux）；移动暂不开放
- 浮层：屏幕中上方，宽 560px，最大高 480px，`--shadow-float` + `--radius-2xl`
- 结构：搜索框 + 分组结果（最近 / 智能体 / 任务 / 文档 / Skill / 跳转）
- 行项 height 36px，左 icon 20px + 右 hint 12px
- 键盘：`↑ ↓` 移动，`Enter` 执行，`Esc` 关闭
- 入口：状态栏右下角"⌘K"提示永驻

### 10.8 状态栏（底部 24px）

桌面底部固定 24px 状态栏，左到右：

```
[●在线] 本地模式 · 已同步 14:32 · 12 条待处理任务 · 张三@anxinai.com               ⌘K
```

- 在线圆点：8px，颜色按 `online/busy/offline`（success / warning / muted）
- 模式：`本地` / `混合` / `云端`，可点击切换（二次确认）
- 同步状态：`已同步 14:32` / `同步中...` / `离线（X 条待推送）` / `冲突 X`（冲突可点击进入解决页）
- 字号 12px，中间用 `·` 分隔，文本 `--text-tertiary`

### 10.9 三态模式视觉（本地 / 混合 / 云端）

| 模式 | 状态栏文案 | 顶部条左侧徽章 | 颜色 |
|---|---|---|---|
| 🔒 本地 | "本地模式 · 数据不出设备" | 🔒 本地 | `--success` |
| 🔄 混合 | "混合模式 · 敏感本地" | 🔄 混合 | `--info` |
| ☁️ 云端 | "云端模式 · 全云端" | ☁️ 云端 | `--im-primary` |

切换需二次确认弹窗，列出"会影响哪些数据 / 哪些功能"。

### 10.10 飞书风 Do / Don't

**Do**
- 主导航条 56px 窄，图标 + 文字标签上下结构
- 列表项 hover/active 状态明确，但不加阴影
- 在线状态在头像右下角显示 10px 圆点 + 1.5px 描边
- 长任务在消息流里以"任务卡"形式 inline（步骤可折叠、可暂停）
- 工具栏图标 20px，按钮 32x32 触控盒
- 多人协作头像组叠加显示，最多 3 个 + "+N"

**Don't**
- 不要用大圆角 24px 卡片（飞书是 8-12px）
- 不要让品牌橙占据聊天/链接/在线状态（飞书是蓝）
- 不要在导航条同时使用图标 + 文字 + 颜色三种激活态（选其一：底色高亮）
- 不要把"远控授权"放在"我"tab 而不在"消息"流里出现 —— 它本质是请求，应该和聊天混排
- 不要在桌面端用大装饰插图（飞书工作台保持克制）

### 10.11 Token 落地约束

所有端必须最终落到**唯一一份语义 token**，按端转译：

| Token | Web (HSL) | Mobile (HEX) | Desktop (HSL) | MP (HEX) | UniApp (HEX) |
|---|---|---|---|---|---|
| `primary` | `25 95% 53%` | `#F97316` | `25 95% 53%` | `#F97316` | `#F97316` |
| `im-primary` | `217 100% 55%` | `#1664FF` | `217 100% 55%` | `#1664FF` | `#1664FF` |
| `success` | `142 76% 36%` | `#16A34A` | `142 76% 36%` | `#16A34A` | `#16A34A` |
| `warning` | `38 92% 50%` | `#F59E0B` | `38 92% 50%` | `#F59E0B` | `#F59E0B` |
| `destructive` | `0 72% 51%` | `#DC2626` | `0 72% 51%` | `#DC2626` | `#DC2626` |
| `info` | `217 91% 60%` | `#3B82F6` | `217 91% 60%` | `#3B82F6` | `#3B82F6` |
| `background` | `0 0% 100%` | `#FFFFFF` | `0 0% 100%` | `#FFFFFF` | `#FFFFFF` |
| `surface-1` | `0 0% 100%` | `#FFFFFF` | `0 0% 100%` | `#FFFFFF` | `#FFFFFF` |
| `surface-2` | `30 14% 98%` | `#FAF8F6` | `30 14% 98%` | `#FAF8F6` | `#FAF8F6` |
| `border` | `30 13% 91%` | `#E8E5E0` | `30 13% 91%` | `#E8E5E0` | `#E8E5E0` |
| `foreground` | `20 14% 10%` | `#1C1A17` | `20 14% 10%` | `#1C1A17` | `#1C1A17` |
| `muted-foreground` | `20 9% 46%` | `#7A736D` | `20 9% 46%` | `#7A736D` | `#7A736D` |

> 旧 mobile `#D4A574` 偏褐色，与 Web `#F97316` 不一致；统一为 `#F97316`（注意保留品牌身份）。

### 10.12 验收

UI 升级完成的判据：

- [ ] 桌面三栏 + 5 一级模块 + 状态栏 + ⌘K
- [ ] 移动 4 tab 命名为"消息 / 任务 / 工作台 / 我"
- [ ] 聊天气泡 user 端用蓝、不用橙
- [ ] 列表项符合 10.5 节规范，0 阴影
- [ ] 圆角全局收到 8/12/16px 阶梯
- [ ] Mobile token `#D4A574` 残留 = 0
- [ ] grep `安心法务` = 0（除归档文档）
- [ ] grep `text-\[#` `bg-\[#` 全仓 = 0

## Changelog

| Date | Change | Reason | Scope |
|------|--------|--------|-------|
| 2026-05-22 | 第 10 节飞书 / 企微对标 | 产品蓝图从"全端工作台"调整为"桌面+移动主战场，Web 官网" | DESIGN.md + 各端 token |
| 2026-04-12 | Initial DESIGN.md | 将审计结论沉淀为项目级设计真相源 | Web design system |
| 2026-04-12 | Token layer Phase 2 | 补全缺失 token、修正 radius/weight 与规范对齐 | index.css, tailwind.config.js, design-tokens.ts |
| 2026-04-12 | Phase 3-5 全站治理 | font-bold/semibold→medium; tracking-wide→caption; 572处hardcoded色→0; focus-visible补齐; DOM嵌套修复 | 138+ files |
| 2026-04-15 | Batch 1 标题层级对齐 | heading token 从 ad-hoc 尺寸对齐到 text-h1/h2/h3 精确 fontSize；新增 heading.display/label | design-tokens.ts, PageContainer.tsx |
| 2026-04-15 | Batch 2 CenterLayout + embedded | 统一中心页面（CaseCenter/ManagementCenter）；PageContainer 新增 embedded 模式解决嵌套标题重复 | 新建 CenterLayout.tsx + 4 pages |
| 2026-04-15 | Batch 3 剩余页面迁移 | MonitoringCenter/Investigation/KnowledgeBase 全部迁移到 PageContainer；92% 页面使用标准布局容器 | 3 pages + RiskAlertPanel |
| 2026-04-15 | Batch 4 硬编码清理 | 硬编码标题 24→0；p-6 padding 34→0；按钮 rounded-lg→rounded-2xl（主要按钮）；tracking-tight→heading tokens | 25+ files |
| 2026-04-15 | 新增统一状态组件 | EmptyState/LoadingState/ErrorState 三组统一 UI 状态组件，替代 72+122+142 文件各自为政的实现 | src/components/common/ |
| 2026-04-15 | Batch 5 桌面端 MVP | Tauri 全局快捷键 Cmd+Shift+Space；参考 ClawX/Qclaw 呼出式交互；多端产品路线图 PRODUCT_ROADMAP.md | desktop/ + PRODUCT_ROADMAP.md |

---

## 11. 业务域可视化（V3 Reset 后核心规范）

> 本节与 §10 飞书规范并存：§10 定义跨端布局/token，§11 定义业务域的"无色彩区分"可视化语言。

V3 安心智能助手覆盖 8 大业务域：法务 / 财务 / 税务 / 合规 / 经营管理 / 调研获客 / 内容产出 / 出海跨境。

### 11.1 核心原则
> **业务域不用色彩区分。** 单一品牌琥珀橙作为唯一彩色锚点，不扩散到 8 个域。

理由（综合 `ui-design` skill + DESIGN.md §1）：
- 8 个高饱和度业务域色形成「通用 SaaS dashboard 拼盘」，违反 §1「不像 SaaS 控制台 / 不强调 AI 感」
- 紫色族业务域色（曾用于"经营管理"）违反 `ui-design` skill FORBIDDEN COLORS
- 业务域是「分类」，不是「状态」；状态色 (`--success/--warning/--destructive`) 才需要色彩

### 11.2 区分手段（克制 → Editorial）
| 手段 | 用法 |
|------|------|
| **序号 01–08** | serif tabular-nums，承载「目录感」 |
| **衬线域名** | Secondary Serif 字体（Noto Serif SC），H1/H2 字号 |
| **Lucide 单色图标** | `Scale` / `Calculator` / `Landmark` / `ShieldCheck` / `LineChart` / `Compass` / `PenLine` / `Globe2`。1.5px stroke，单色 `text-foreground/70` |
| **Micro tracker** | `LABELEN · 01` 形如「LEGAL · 01」，0.16em UPPERCASE tracking |
| **字距 + 字号层次** | 取代色彩层次 |

❌ **禁止用** 8 种颜色卡片墙、emoji 图标、域色 stripe、域色 dot、域色 underline。

### 11.3 业务域元数据真相源
唯一注册表：[`frontend/src/lib/domains.ts`](frontend/src/lib/domains.ts)
- `DOMAINS: readonly DomainMeta[]` — 按固定顺序 (legal → global) 暴露
- `DomainMeta` 字段：`id / label / labelEn / tagline / defaultPath / icon`（**无 color/surface/cssVar**）
- `inferDomainFromPath(pathname)` — 由路径推断业务域

跨端同步：
- `mobile/src/theme/colors.ts` → `domainMeta`（仅 labelZh/labelEn）
- `mini-program/src/styles/design-tokens.ts` → `domainMeta`（同上）

### 11.4 落地组件（5 个原子）
| 组件 | 文件 | 用途 |
|------|------|------|
| `<DomainBadge>` | `components/ui/domain.tsx` | micro UPPERCASE 文字「LEGAL · 法务」 |
| `<DomainStripe>` | 同上 | Reset 后保留为 no-op shim（旧版 4pt 彩条已废除） |
| `<DomainCard>` | 同上 | 序号 + 衬线名 + tagline + Lucide + → 图标，1px hairline 边 |
| `<DomainGrid>` | 同上 | 编辑级 2 列目录（**不是** 4×2 卡片墙） |
| `<DomainBreadcrumb>` | `components/ui/DomainBreadcrumb.tsx` | 纯文字 micro UPPERCASE「LEGAL · 法务 · 合同审查」 |

### 11.5 守护断言（防回归）
跨端 vitest 已对以下违规行为加反向断链 fail：
- 任何 `--domain-*` CSS 变量
- 任何 `colors.domain.*` Tailwind utility
- 任何 8 域专属 hex 在 token 文件
- 紫色族 hue 260-290 在 design token 变量
- `Inter` / `system-ui` / `-apple-system` / `Helvetica` / `Roboto` 等 FORBIDDEN FONTS
- emoji 字面值在业务组件源码

详细 95+ 条断言：`frontend/src/brand-consistency.test.ts` + `mobile/src/brand-consistency.test.ts` + `mini-program/src/styles/design-tokens.test.ts` 等

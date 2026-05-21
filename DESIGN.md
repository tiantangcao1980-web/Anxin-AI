# 安心智能助手 DESIGN.md

> **单一设计真相源**（视觉令牌 / 排版 / 组件外观 / 布局 / 动效 / Icon 体系）。
> 工程实现规则（命名 / 状态管理 / API / 路由 / 测试）见 [`docs/standards/frontend-standard.md`](docs/standards/frontend-standard.md)。
> `docs/design-system.md` 保留实现说明与历史背景；当三者冲突时，**本文件为准**。
> 适用范围：`frontend/` Web 主界面优先，随后同步到 `mobile/` 与 `mini-program/`。

---

## ⚠️ 2026-05 Reset 公告（必读）

PR #9 上轮 V3 升级落地了「8 业务域 × 8 高饱和色拼盘 + emoji 图标 + Inter 字体」方案，
违反 `ui-design` skill 多条硬性禁令（FORBIDDEN COLORS / FORBIDDEN FONTS / NEVER USE EMOJI），
也违反本文件 §1 写的「不像 SaaS 控制台 / 不强调 AI 感」原则。

**2026-05 Reset 后的设计方向**：
- **Aesthetic Direction**：**Editorial Luxury**（克制的奢华 · 编辑级排版）
- **业务域可视化**：不用色彩区分（见 §10）。用序号 01–08 + 衬线域名 + Lucide 图标 + 字距层次
- **品牌色**：单一琥珀橙 `--primary` 仅出现在 CTA / 1px active 线 / 焦点环
- **字体**：中文系统字体（PingFang SC / Microsoft YaHei / Noto Sans SC）+ Editorial Serif（Noto Serif SC）
- **图标**：Lucide（Web）/ Ionicons（RN 平台 API） — 全单色线性，**禁用 emoji 作 UI 图标**

详细 Reset 记录：[docs/design/ui-audit-and-upgrade-2026-05.md](docs/design/ui-audit-and-upgrade-2026-05.md)
独立 Prototype：[docs/design/v3-prototype-editorial.html](docs/design/v3-prototype-editorial.html)

下文 §1-§9 的内容仍是设计真相源，但 §3 字体表与 §10（新增）覆盖了 Reset 后的最终决策；如有冲突以 Reset 章节为准。

---

## ⚙️ 2026-05-21 S9 工程协作密度增量（必读补充）

**目标**：保留 Editorial Luxury 在「品牌入口 / 内容阅读」上的资产（Login / Hero / Display / Editorial Serif），同时在「应用功能容器」（chat / personas / admin / case-center 等）层向**飞书 / 企业微信工程协作密度**靠拢。

**飞书 / 企业微信参考点**：
- 应用 navbar 48-56px（紧凑）
- 卡片圆角 8-12px、按钮圆角 6-8px（克制，不张扬）
- 阴影极轻，主要靠 1px 边框 + `border/60` 描边
- 列表行高 36-40px（紧凑扫描）
- 工作台卡片化模块直达

**S9 实际落地的 token 收紧**（详见 `frontend/src/lib/design-tokens.ts`）：

| Token | Reset 后（Editorial Luxury） | S9 后（应用容器层）| 备注 |
|---|---|---|---|
| `radius.button` | `rounded-2xl` (16px) | **`rounded-lg` (8px)** | 飞书风按钮 |
| `radius.card` | `rounded-3xl` (24px) | **`rounded-xl` (12px)** | 飞书风卡片 |
| `radius.bubble` | `rounded-2xl` (16px) | **`rounded-xl` (12px)** | 紧凑气泡 |
| `radius.small` | `rounded-lg` (8px) | **`rounded-md` (6px)** | 小控件 |
| `radius.hero` | — | **`rounded-3xl` (24px)** | **新增**，保留 Editorial Hero 大圆角语义 |
| `cardStyle.base` shadow | `shadow-card` | **`shadow-sm`** | 弱阴影 |
| `cardStyle.base` border | `border/40` | **`border/60`** | 加强边框描边 |
| Layout navbar | `h-[60px]` | **`h-14` (56px)** | 紧凑导航 |
| 按钮 hover | `hover:-translate-y-0.5` | 移除（直接颜色变化）| 工程协作风去除"浮动"动画 |

**保留的 Editorial 资产**：
- Login / WelcomeGuide / DomainHomePage 的 Display Hero（48px Noto Serif SC）
- 业务域名仍用衬线展示
- 品牌琥珀橙不变
- 文档预览区仍用 Editorial 字号体系

**判断准则**：你正在做的是「**功能容器**」还是「**品牌入口 / 内容阅读**」？
- 前者用 S9 紧凑 token（飞书风）
- 后者用 Editorial Hero token（保留 Reset 后定型）

---

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

### Font Families (Reset 后)
- **Primary Sans**: `"PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif`
  - ❌ 禁用 `Inter` / `Roboto` / `Arial` / `Helvetica` / `Helvetica Neue` / `system-ui` / `-apple-system` / `BlinkMacSystemFont`（`ui-design` skill FORBIDDEN FONTS）
- **Secondary Serif**: `"Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif`
  - Reset 后**升级为 Display + H1 + 业务域名 + 文档预览的主担字体**（承载 Editorial Luxury 气质）
- **Monospace**: `"JetBrains Mono", "SF Mono", "Menlo", "Monaco", "Consolas", monospace`

### Hierarchy Table (Reset 后 — Editorial Luxury)

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | **Secondary Serif** | 48px | 500 | 1.1 | -0.04em | Login / DomainHomePage / WelcomeGuide |
| Page Title (H1) | **Secondary Serif** | 32px | 500 | 1.2 | -0.02em | 业务子页主标题、业务域名 |
| Section Title (H2) | Primary Sans | 24px | 500 | 1.3 | -0.01em | 区块标题 |
| Panel Title (H3) | Primary Sans | 18px | 600 | 1.4 | -0.005em | 卡片/面板标题 |
| Lead Body | Primary Sans | 16px | 400 | 1.75 | 0 | 长文本、AI 回复 |
| Body | Primary Sans | 15px | 400 | 1.65 | 0 | 标准正文 |
| Small Body | Primary Sans | 13px | 400 | 1.6 | 0 | 表格、说明 |
| Caption | Primary Sans | 13px | 400 | 1.5 | 0.01em | 时间戳、弱标签 |
| **Micro tracker** | **Primary Sans** | **11px** | **500** | **1.4** | **0.16em** UPPERCASE | Editorial 标志细节 — 「LEGAL · 01」「INDEX · 业务域目录」类元信息 |
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

<a id="icon-system"></a>
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

## 10. 业务域可视化（V3 Reset 后核心规范）

V3 安心智能助手覆盖 8 大业务域：法务 / 财务 / 税务 / 合规 / 经营管理 / 调研获客 / 内容产出 / 出海跨境。

### 10.1 核心原则
> **业务域不用色彩区分。** 单一品牌琥珀橙作为唯一彩色锚点，不扩散到 8 个域。

理由（综合 `ui-design` skill + DESIGN.md §1）：
- 8 个高饱和度业务域色形成「通用 SaaS dashboard 拼盘」，违反 §1「不像 SaaS 控制台 / 不强调 AI 感」
- 紫色族业务域色（曾用于"经营管理"）违反 `ui-design` skill FORBIDDEN COLORS
- 业务域是「分类」，不是「状态」；状态色 (`--success/--warning/--destructive`) 才需要色彩

### 10.2 区分手段（克制 → Editorial）
| 手段 | 用法 |
|------|------|
| **序号 01–08** | serif tabular-nums，承载「目录感」 |
| **衬线域名** | Secondary Serif 字体（Noto Serif SC），H1/H2 字号 |
| **Lucide 单色图标** | `Scale` / `Calculator` / `Landmark` / `ShieldCheck` / `LineChart` / `Compass` / `PenLine` / `Globe2`。1.5px stroke，单色 `text-foreground/70` |
| **Micro tracker** | `LABELEN · 01` 形如「LEGAL · 01」，0.16em UPPERCASE tracking |
| **字距 + 字号层次** | 取代色彩层次 |

❌ **禁止用** 8 种颜色卡片墙、emoji 图标、域色 stripe、域色 dot、域色 underline。

### 10.3 业务域元数据真相源
唯一注册表：[`frontend/src/lib/domains.ts`](frontend/src/lib/domains.ts)
- `DOMAINS: readonly DomainMeta[]` — 按固定顺序 (legal → global) 暴露
- `DomainMeta` 字段：`id / label / labelEn / tagline / defaultPath / icon`（**无 color/surface/cssVar**）
- `inferDomainFromPath(pathname)` — 由路径推断业务域

跨端同步：
- `mobile/src/theme/colors.ts` → `domainMeta`（仅 labelZh/labelEn）
- `mini-program/src/styles/design-tokens.ts` → `domainMeta`（同上）

### 10.4 落地组件（5 个原子）
| 组件 | 文件 | 用途 |
|------|------|------|
| `<DomainBadge>` | `components/ui/domain.tsx` | micro UPPERCASE 文字「LEGAL · 法务」 |
| `<DomainStripe>` | 同上 | Reset 后保留为 no-op shim（旧版 4pt 彩条已废除） |
| `<DomainCard>` | 同上 | 序号 + 衬线名 + tagline + Lucide + → 图标，1px hairline 边 |
| `<DomainGrid>` | 同上 | 编辑级 2 列目录（**不是** 4×2 卡片墙） |
| `<DomainBreadcrumb>` | `components/ui/DomainBreadcrumb.tsx` | 纯文字 micro UPPERCASE「LEGAL · 法务 · 合同审查」 |

### 10.5 落地页面
| 页面 | 关键设计 |
|------|----------|
| Login (`/login`) | 7+5 不对称 grid · 左侧 serif Display + 8 域 serif 编号目录 |
| DomainHomePage (`/domains`) | 4+8 编辑部双栏 · 左 8 业务域 serif 名录 · 右当前域子页列 |
| WelcomeGuide modal | 首登触发 · 编辑部目录式 8 行 · 单 CTA「打开 AI 对话」 |
| Layout 顶栏 | active = 1px primary underline（**非业务域色** underline）|
| Layout 侧栏 | active = 1px primary 左线（**非业务域** stripe / dot）|
| 业务子页 | `<DomainBreadcrumb>` + 序号 + 衬线 H1，**不要** `<DomainStripe>` 4pt 彩条 |

### 10.6 守护断言（防回归）
跨端 vitest 已对以下违规行为加反向断链 fail：
- 任何 `--domain-*` CSS 变量
- 任何 `colors.domain.*` Tailwind utility
- 任何 8 域专属 hex 在 token 文件
- 紫色族 hue 260-290 在 design token 变量
- `Inter` / `system-ui` / `-apple-system` / `Helvetica` / `Roboto` 等 FORBIDDEN FONTS
- emoji 字面值在业务组件源码

详细 95+ 条断言：`frontend/src/brand-consistency.test.ts` + `mobile/src/brand-consistency.test.ts` + `mini-program/src/styles/design-tokens.test.ts` 等

---

## Changelog

| Date | Change | Reason | Scope |
|------|--------|--------|-------|
| 2026-04-12 | Initial DESIGN.md | 将审计结论沉淀为项目级设计真相源 | Web design system |
| 2026-04-12 | Token layer Phase 2 | 补全缺失 token、修正 radius/weight 与规范对齐 | index.css, tailwind.config.js, design-tokens.ts |
| 2026-04-12 | Phase 3-5 全站治理 | font-bold/semibold→medium; tracking-wide→caption; 572处hardcoded色→0; focus-visible补齐; DOM嵌套修复 | 138+ files |
| 2026-04-15 | Batch 1 标题层级对齐 | heading token 从 ad-hoc 尺寸对齐到 text-h1/h2/h3 精确 fontSize；新增 heading.display/label | design-tokens.ts, PageContainer.tsx |
| 2026-04-15 | Batch 2 CenterLayout + embedded | 统一中心页面（CaseCenter/ManagementCenter）；PageContainer 新增 embedded 模式解决嵌套标题重复 | 新建 CenterLayout.tsx + 4 pages |
| 2026-04-15 | Batch 3 剩余页面迁移 | MonitoringCenter/Investigation/KnowledgeBase 全部迁移到 PageContainer；92% 页面使用标准布局容器 | 3 pages + RiskAlertPanel |
| 2026-04-15 | Batch 4 硬编码清理 | 硬编码标题 24→0；p-6 padding 34→0；按钮 rounded-lg→rounded-2xl（主要按钮）；tracking-tight→heading tokens | 25+ files |
| 2026-04-15 | 新增统一状态组件 | EmptyState/LoadingState/ErrorState 三组统一 UI 状态组件，替代 72+122+142 文件各自为政的实现 | src/components/common/ |
| 2026-04-15 | Batch 5 桌面端 MVP | Tauri 全局快捷键 Cmd+Shift+Space；参考 ClawX/Qclaw 呼出式交互；多端产品路线图 PRODUCT_ROADMAP.md | desktop/ + PRODUCT_ROADMAP.md |
| 2026-05-20 | **Editorial Luxury Reset** | 按 `ui-design` skill 标准全量 Reset：删 8 域高饱和色（含违禁紫色）+ 删 Inter/system-ui FORBIDDEN FONTS + 删 emoji 图标。Aesthetic Direction 确认为 Editorial Luxury。8 业务域改用 序号+衬线+Lucide 区分。新增 §10 业务域可视化规范 + 95+ 跨端反向断链守护。 | 三端 token + 5 原子组件 + 4 落地页 + DESIGN.md + ui-audit doc |

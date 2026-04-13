/**
 * design-tokens.ts - 设计令牌系统
 *
 * ===== 统一设计规范 =====
 * 集中管理颜色、间距、圆角、阴影等视觉常量
 * 所有组件必须通过此文件的 token 来引用样式，禁止硬编码
 *
 * 设计原则：
 * - 企业级规范：干净、整洁、专业（参考豆包/Apple/大疆设计语言）
 * - 无蓝紫渐变和"AI味"元素
 * - 统一的图标尺寸体系
 * - 一致的交互反馈
 * - 全部使用 CSS 变量语义色，支持深色模式
 *
 * 颜色映射（禁止硬编码 iOS hex）：
 * - #007AFF → bg-primary / text-primary
 * - #1C1C1E → text-foreground
 * - #8E8E93 → text-muted-foreground
 * - #F2F2F7 → bg-muted
 * - #E5E5EA → border-border
 * - #3C3C43 → text-foreground/80
 * - #FF3B30 → text-destructive
 * - #34C759 → statusColor.success
 * - #FF9500 → statusColor.warning
 * - #AEAEB2 → placeholder:text-muted-foreground
 * - #F5F5F7 → bg-muted
 */

// ===== 图标尺寸体系 =====
export const iconSize = {
  /** 极小图标：标签、状态指示 - 12px */
  xs: 'w-3 h-3',
  /** 小图标：内联文本旁 - 16px */
  sm: 'w-4 h-4',
  /** 默认图标：导航、按钮内 - 20px */
  md: 'w-5 h-5',
  /** 大图标：空状态、页面标题 - 24px */
  lg: 'w-6 h-6',
  /** 特大图标：空状态插图 - 32px */
  xl: 'w-8 h-8',
  /** 巨大图标：首屏装饰 - 48px */
  '2xl': 'w-12 h-12',
} as const

// ===== 间距体系 =====
export const spacing = {
  page: 'px-4 py-4 sm:px-5 sm:py-5 lg:px-6 lg:py-6',
  pageMobile: 'px-4 py-4',
  card: 'p-5',
  cardCompact: 'p-4',
  section: 'space-y-6',
  sectionCompact: 'space-y-4',
} as const

// ===== 圆角体系 (DESIGN.md §5 Radius Scale) =====
export const radius = {
  /** 按钮、输入框 — 16px */
  button: 'rounded-2xl',
  /** 标准卡片、面板、抽屉 — 24px */
  card: 'rounded-3xl',
  /** 弹窗 — 24px */
  dialog: 'rounded-3xl',
  /** 头像 — pill */
  avatar: 'rounded-full',
  /** 标签、徽章 — 4px */
  badge: 'rounded',
  /** 聊天气泡 — 16px */
  bubble: 'rounded-2xl',
  /** 紧凑容器、列表子项 — 12px */
  compact: 'rounded-xl',
  /** 小控件、表格行 — 8px */
  small: 'rounded-lg',
} as const

// ===== 阴影体系 =====
export const shadow = {
  card: 'shadow-card transition-shadow',
  dialog: 'shadow-float',
  dropdown: 'shadow-float',
  float: 'shadow-card',
} as const

// ===== 动画时长 =====
export const duration = {
  fast: 'duration-150',
  normal: 'duration-200',
  slow: 'duration-300',
} as const

// ===== 卡片样式预设 (DESIGN.md §4 Cards: 24px radius) =====
export const cardStyle = {
  base: 'rounded-3xl border border-border/70 bg-surface-1 p-5 shadow-card',
  interactive:
    'rounded-3xl border border-border/70 bg-surface-1 p-5 shadow-card transition-all hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-float cursor-pointer',
  highlight: 'rounded-3xl border border-primary/20 bg-primary-50/80 p-5 shadow-card dark:bg-primary-100/10',
  compact: 'rounded-2xl border border-border/70 bg-surface-1 p-4 shadow-card',
  flat: 'rounded-2xl bg-surface-2 p-5',
} as const

// ===== 按钮样式预设 (DESIGN.md §4 Buttons: 16px radius) =====
export const buttonStyle = {
  primary:
    'rounded-2xl bg-primary text-primary-foreground px-4 py-2 text-sm font-medium shadow-sm transition-all hover:-translate-y-0.5 hover:bg-primary-600 active:translate-y-0 outline-none focus-visible:ring-[3px] focus-visible:ring-primary/20 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  secondary:
    'rounded-2xl border border-border/70 bg-surface-1 px-4 py-2 text-sm font-medium text-foreground transition-all hover:bg-surface-2 hover:border-primary/20 outline-none focus-visible:ring-[3px] focus-visible:ring-primary/15 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  ghost:
    'rounded-2xl px-4 py-2 text-sm font-medium text-muted-foreground transition-all hover:bg-surface-2 hover:text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-primary/15 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  danger:
    'rounded-2xl bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground transition-all hover:bg-destructive/90 outline-none focus-visible:ring-[3px] focus-visible:ring-destructive/20 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  icon: 'rounded-2xl p-2 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-primary/15 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  sm: 'rounded-xl px-3 py-1.5 text-xs font-medium transition-all outline-none focus-visible:ring-[3px] focus-visible:ring-primary/15 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
} as const

// DESIGN.md §3: 中文标题使用 font-medium (500)，避免 font-semibold (600) 带来的压迫感
export const heading = {
  page: 'text-2xl sm:text-3xl font-medium tracking-heading-lg text-foreground',
  section: 'text-lg sm:text-xl font-medium tracking-heading-md text-foreground',
  card: 'text-sm sm:text-base font-medium text-foreground',
  muted: 'text-sm text-muted-foreground',
  micro: 'text-xs text-muted-foreground',
} as const

// ===== 状态颜色 =====
// 使用语义化 CSS 变量色，支持深色模式
export const statusColor = {
  success: 'bg-success/10 text-success dark:bg-success/20',
  warning: 'bg-warning/10 text-warning dark:bg-warning/20',
  error: 'bg-destructive/10 text-destructive dark:bg-destructive/20',
  info: 'bg-info/10 text-info dark:bg-info/20',
  neutral: 'bg-muted text-muted-foreground',
} as const

// ===== 状态徽章 =====
export const statusBadge = {
  success: 'border border-success/20 bg-success/10 text-success dark:bg-success/20',
  warning: 'border border-warning/20 bg-warning/10 text-warning dark:bg-warning/20',
  error: 'border border-destructive/20 bg-destructive/10 text-destructive dark:bg-destructive/20',
  info: 'border border-info/20 bg-info/10 text-info dark:bg-info/20',
  neutral: 'border border-border bg-muted text-muted-foreground',
} as const

// ===== 聊天气泡样式 =====
export const chatBubble = {
  /** 用户消息 */
  user: 'bg-primary text-primary-foreground px-4 py-2.5 rounded-2xl rounded-br-md',
  /** AI 消息 */
  ai: 'bg-muted/60 border border-border text-foreground px-4 py-3 rounded-2xl rounded-bl-md',
  /** 系统消息 */
  system: 'text-[11px] font-medium px-4 py-1.5 rounded-full',
  /** 系统消息-错误 */
  systemError: 'bg-destructive/8 text-destructive border border-destructive/20',
  /** 系统消息-警告 */
  systemWarning: 'bg-warning/8 text-warning border border-warning/20',
} as const

// ===== 输入框样式 =====
export const inputStyle = {
  chatContainer: 'relative flex items-end rounded-2xl border border-border/70 bg-surface-1 shadow-card transition-all focus-within:border-primary/35 focus-within:ring-2 focus-within:ring-primary/10',
  chatTextarea: 'flex-1 bg-transparent py-2.5 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none border-none resize-none',
  search: 'w-full rounded-xl border border-border/70 bg-surface-1 px-3 py-2 text-sm text-foreground shadow-sm transition-all placeholder:text-muted-foreground focus:border-primary/35 focus:outline-none focus:ring-2 focus:ring-primary/10 focus-visible:border-primary/35 focus-visible:ring-2 focus-visible:ring-primary/10 disabled:cursor-not-allowed disabled:opacity-50',
} as const

// ===== Prose 样式（Markdown 渲染） =====
export const proseStyle = {
  /** 聊天消息中的 Markdown */
  chat: 'prose prose-sm max-w-none prose-headings:text-foreground prose-headings:font-medium prose-p:text-foreground prose-p:leading-relaxed prose-strong:text-foreground prose-ul:text-foreground/80 prose-ol:text-foreground/80 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-[13px] prose-pre:bg-foreground prose-pre:text-background dark:prose-invert',
} as const

// ===== 侧边栏导航 =====
export const sidebarNav = {
  /** 模块标题 */
  title: 'text-sm font-bold text-foreground',
  /** 导航项字号 - 14px */
  itemText: 'text-sm',
  /** 导航项激活态 */
  itemActive: 'bg-primary/10 text-primary font-medium outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:ring-offset-2',
  /** 导航项默认态 */
  itemDefault: 'text-muted-foreground hover:bg-muted hover:text-foreground outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-primary/15 focus-visible:ring-offset-2',
} as const

// ===== 侧边栏列表项 =====
export const listItem = {
  /** 默认列表项 */
  base: 'text-foreground/80 hover:bg-muted border border-transparent',
  /** 选中/激活列表项 */
  active: 'bg-primary/5 text-primary border border-primary/10',
  /** 批量选中列表项 */
  selected: 'bg-destructive/5 text-destructive border border-destructive/10',
} as const

// ===== 覆盖层 =====
export const overlay = {
  /** 模态遮罩 */
  backdrop: 'fixed inset-0 bg-black/20 backdrop-blur-sm z-50',
  /** 底部弹出层 */
  drawer: 'bg-background rounded-t-2xl shadow-xl',
} as const

// ===== 工具栏按钮 =====
export const toolbarButton = {
  /** 工具栏默认按钮 */
  base: 'p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/15 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  /** 工具栏激活按钮 */
  active: 'p-1.5 text-primary bg-primary/5 hover:bg-primary/10 rounded-lg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
} as const

// ===== 在线状态指示 =====
export const onlineIndicator = {
  dot: 'w-1.5 h-1.5 rounded-full',
  online: 'bg-emerald-500',
  busy: 'bg-amber-500',
  offline: 'bg-muted-foreground/30',
} as const

// ===== AI 状态样式 =====
export const aiStatus = {
  /** AI 思考中（脉冲动画） */
  thinking: 'text-ai animate-ai-pulse',
  /** AI 流式输出光标 */
  cursor: 'inline-block w-0.5 h-4 bg-ai animate-ai-cursor ml-0.5',
  /** AI 消息气泡背景 */
  surface: 'bg-ai-surface',
  /** AI 标识色文字 */
  label: 'text-ai font-medium',
  /** AI 错误/降级 */
  error: 'text-destructive border border-destructive/20 bg-destructive/5 rounded-lg p-3',
} as const

// ===== 模型选择器 =====
export const modelSelector = {
  trigger: 'flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors cursor-pointer',
  dropdown: 'bg-popover border border-border rounded-xl shadow-lg p-1 min-w-[200px]',
  option: 'flex items-center justify-between px-3 py-2 text-sm rounded-lg hover:bg-muted cursor-pointer transition-colors',
  optionActive: 'flex items-center justify-between px-3 py-2 text-sm rounded-lg bg-primary/5 text-primary font-medium',
  badge: 'text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground',
  badgeDefault: 'text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary',
} as const

// ===== 搜索栏 (DESIGN.md §4 Search Input: 16px radius) =====
export const searchBar = {
  container: 'relative',
  input: 'w-full rounded-2xl border border-border/70 bg-surface-1 py-2 pl-9 pr-3 text-sm text-foreground shadow-sm transition-all placeholder:text-muted-foreground focus:border-primary/35 focus:outline-none focus:ring-2 focus:ring-primary/10',
  icon: 'absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground',
  clear: 'absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground',
} as const

// ===== 收藏按钮 =====
export const starButton = {
  base: 'p-1 rounded-md transition-colors',
  active: 'text-amber-500 hover:text-amber-600',
  inactive: 'text-muted-foreground/40 hover:text-amber-400',
} as const

// ===== 图表色板 =====
export const chartColors = [
  'hsl(var(--primary))',
  'hsl(var(--info))',
  'hsl(var(--success))',
  'hsl(var(--warning))',
  'hsl(var(--destructive))',
  'hsl(var(--ai))',
] as const

// ===== 图谱节点色板 =====
// 这些 hex 值是 canvas 绘图的 fallback（CSS variables 无法直接用于 canvas API）。
// 在非 canvas 场景（CSS / Tailwind）应优先使用 `bg-node-law` 等语义工具类。
// 对应 CSS 变量：--node-law, --node-case, --node-party, --node-organization,
//               --node-lawyer, --node-query, --node-conclusion, --node-other
export const graphNodeColors = {
  law: '#1a9e52',
  case: '#2563eb',
  party: '#d97706',
  organization: '#7c3aed',
  lawyer: '#ea6a10',
  query: '#64748b',
  conclusion: '#9333ea',
  other: '#6b7280',
} as const

// ===== 协作身份色板 =====
export const collaborationAccentColors = [
  'hsl(var(--primary))',
  '#4ECDC4',
  'hsl(var(--info))',
  'hsl(var(--success))',
  'hsl(var(--warning))',
  '#A29BFE',
  '#FD79A8',
  '#E17055',
] as const

// ===== 合规评分色板 =====
export const complianceScoreColors = {
  excellent: 'hsl(160 60% 45%)',
  good: 'hsl(var(--primary))',
  medium: 'hsl(35 90% 55%)',
  poor: 'hsl(350 65% 55%)',
} as const

// ===== 风险等级色板 =====
export const riskLevelColors = {
  critical: 'hsl(var(--destructive))',
  high: 'hsl(var(--warning))',
  medium: 'hsl(var(--primary))',
  low: graphNodeColors.other,
} as const

// ===== 图谱画布色板 =====
export const graphCanvasColors = {
  dark3d: '#0f172a',
  dark2d: '#1e1e1e',
  light3d: '#f8fafc',
  light2d: '#fafafa',
  labelDark: '#e2e8f0',
  labelLight: '#334155',
  linkDark: 'rgba(148, 163, 184, 0.3)',
  linkLight: 'rgba(100, 116, 139, 0.35)',
  tooltipDarkBg: 'rgba(15, 23, 42, 0.8)',
  tooltipLightBg: 'rgba(255, 255, 255, 0.9)',
  tooltipLightShadow: '0 1px 3px rgba(0,0,0,0.1)',
  particle: '#818cf8',
} as const

// ===== 编辑器色板 =====
export const editorPalette = {
  text: [
    '#2f241d',
    '#5f5148',
    '#81746b',
    '#a79a90',
    graphNodeColors.other,
    graphNodeColors.party,
    'hsl(var(--warning))',
    graphNodeColors.law,
    graphNodeColors.case,
    graphNodeColors.organization,
    graphNodeColors.conclusion,
    graphNodeColors.lawyer,
  ],
  highlight: 'hsl(var(--warning) / 0.35)',
  printText: '#2f241d',
  printBorder: '#8c7e73',
  printHeaderBg: '#f6f0e8',
} as const

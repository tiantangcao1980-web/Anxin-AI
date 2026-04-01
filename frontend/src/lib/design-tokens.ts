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
  /** 页面内边距 */
  page: 'px-6 py-6',
  pageMobile: 'px-4 py-4',
  /** 卡片内边距 */
  card: 'p-5',
  cardCompact: 'p-4',
  /** 区块间距 */
  section: 'space-y-6',
  sectionCompact: 'space-y-4',
} as const

// ===== 圆角体系 =====
export const radius = {
  /** 按钮、输入框 */
  button: 'rounded-lg',
  /** 卡片 */
  card: 'rounded-xl',
  /** 弹窗 */
  dialog: 'rounded-2xl',
  /** 头像 */
  avatar: 'rounded-full',
  /** 标签 */
  badge: 'rounded-md',
  /** 聊天气泡 */
  bubble: 'rounded-2xl',
} as const

// ===== 阴影体系 =====
export const shadow = {
  /** 卡片悬浮 */
  card: 'shadow-sm hover:shadow-md transition-shadow',
  /** 弹窗 */
  dialog: 'shadow-xl',
  /** 下拉菜单 */
  dropdown: 'shadow-lg',
  /** 浮动按钮 */
  float: 'shadow-md',
} as const

// ===== 动画时长 =====
export const duration = {
  fast: 'duration-150',
  normal: 'duration-200',
  slow: 'duration-300',
} as const

// ===== 卡片样式预设 =====
export const cardStyle = {
  /** 基础卡片 */
  base: 'bg-background border border-border rounded-xl p-5',
  /** 可交互卡片（hover 效果） */
  interactive:
    'bg-background border border-border rounded-xl p-5 hover:shadow-md hover:border-primary/20 transition-all cursor-pointer',
  /** 高亮卡片 */
  highlight: 'bg-primary/5 border border-primary/20 rounded-xl p-5',
  /** 紧凑卡片 */
  compact: 'bg-background border border-border rounded-xl p-4',
  /** 无边框卡片 */
  flat: 'bg-muted/50 rounded-xl p-5',
} as const

// ===== 按钮样式预设 =====
export const buttonStyle = {
  /** 主要按钮 */
  primary:
    'bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98] rounded-lg px-4 py-2 text-sm font-medium transition-all',
  /** 次要按钮 */
  secondary:
    'bg-muted text-foreground hover:bg-muted/80 active:scale-[0.98] rounded-lg px-4 py-2 text-sm font-medium transition-all',
  /** 幽灵按钮 */
  ghost:
    'text-muted-foreground hover:bg-muted hover:text-foreground active:scale-[0.98] rounded-lg px-4 py-2 text-sm font-medium transition-all',
  /** 危险按钮 */
  danger:
    'bg-destructive text-destructive-foreground hover:bg-destructive/90 active:scale-[0.98] rounded-lg px-4 py-2 text-sm font-medium transition-all',
  /** 图标按钮（无文字） */
  icon: 'p-2 text-muted-foreground hover:bg-muted hover:text-foreground rounded-lg transition-colors',
  /** 小号按钮 */
  sm: 'px-3 py-1.5 text-xs font-medium rounded-lg transition-all',
} as const

// ===== 页面标题样式 =====
// 紧凑层级：page(14px) ≥ section(14px) > card(13px) > muted(12px) > micro(11px)
export const heading = {
  /** 页面主标题 - 14px */
  page: 'text-sm font-semibold text-foreground',
  /** 区块标题 - 14px（与 page 同级，通过上下文区分） */
  section: 'text-sm font-semibold text-foreground',
  /** 卡片标题 - 13px */
  card: 'text-[13px] font-medium text-foreground',
  /** 辅助文本 - 12px */
  muted: 'text-xs text-muted-foreground',
  /** 微标签 - 11px */
  micro: 'text-[11px] text-muted-foreground',
} as const

// ===== 状态颜色 =====
// 使用语义化 CSS 变量色，支持深色模式
export const statusColor = {
  success: 'text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950/30',
  warning: 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-950/30',
  error: 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950/30',
  info: 'text-primary bg-primary/5',
  neutral: 'text-muted-foreground bg-muted',
} as const

// ===== 状态徽章 =====
export const statusBadge = {
  success: 'text-emerald-700 bg-emerald-50 border border-emerald-200 dark:text-emerald-400 dark:bg-emerald-950/30 dark:border-emerald-800',
  warning: 'text-amber-700 bg-amber-50 border border-amber-200 dark:text-amber-400 dark:bg-amber-950/30 dark:border-amber-800',
  error: 'text-red-700 bg-red-50 border border-red-200 dark:text-red-400 dark:bg-red-950/30 dark:border-red-800',
  info: 'text-primary bg-primary/5 border border-primary/20',
  neutral: 'text-muted-foreground bg-muted border border-border',
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
  systemError: 'bg-red-50 text-red-600 border border-red-200 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800',
  /** 系统消息-警告 */
  systemWarning: 'bg-amber-50 text-amber-600 border border-amber-200 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-800',
} as const

// ===== 输入框样式 =====
export const inputStyle = {
  /** 聊天输入框容器 */
  chatContainer: 'relative flex items-end bg-muted/50 rounded-2xl border border-border focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/10 transition-all',
  /** 聊天文本域 */
  chatTextarea: 'flex-1 py-2.5 bg-transparent border-none resize-none focus:outline-none text-foreground placeholder:text-muted-foreground text-sm leading-relaxed',
  /** 搜索输入框 */
  search: 'w-full bg-muted/50 border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 transition-all',
} as const

// ===== Prose 样式（Markdown 渲染） =====
export const proseStyle = {
  /** 聊天消息中的 Markdown */
  chat: 'prose prose-sm max-w-none prose-headings:text-foreground prose-headings:font-semibold prose-p:text-foreground prose-p:leading-relaxed prose-strong:text-foreground prose-ul:text-foreground/80 prose-ol:text-foreground/80 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-[13px] prose-pre:bg-foreground prose-pre:text-background dark:prose-invert',
} as const

// ===== 侧边栏导航 =====
export const sidebarNav = {
  /** 模块标题 */
  title: 'text-sm font-bold text-foreground',
  /** 导航项字号 - 14px */
  itemText: 'text-sm',
  /** 导航项激活态 */
  itemActive: 'bg-primary/10 text-primary font-medium',
  /** 导航项默认态 */
  itemDefault: 'text-muted-foreground hover:bg-muted hover:text-foreground',
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
  base: 'p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors',
  /** 工具栏激活按钮 */
  active: 'p-1.5 text-primary bg-primary/5 hover:bg-primary/10 rounded-lg transition-colors',
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

// ===== 搜索栏 =====
export const searchBar = {
  container: 'relative',
  input: 'w-full bg-muted/50 border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 transition-all',
  icon: 'absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground',
  clear: 'absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors',
} as const

// ===== 收藏按钮 =====
export const starButton = {
  base: 'p-1 rounded-md transition-colors',
  active: 'text-amber-500 hover:text-amber-600',
  inactive: 'text-muted-foreground/40 hover:text-amber-400',
} as const

// ===== 图表色板 =====
export const chartColors = [
  'hsl(var(--primary))',          // 品牌琥珀橙
  'hsl(160, 60%, 45%)',           // 翡翠绿
  'hsl(35, 90%, 55%)',            // 琥珀橙
  'hsl(200, 70%, 50%)',           // 天际蓝
  'hsl(350, 65%, 55%)',           // 珊瑚红
  'hsl(var(--ai))',               // AI 紫
] as const

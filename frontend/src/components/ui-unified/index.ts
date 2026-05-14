/**
 * UI Unified — 业务页统一脚手架层 (Phase I ADR 003 主推目录)
 *
 * 本目录提供「一致性结构上不再可能被破坏」的复合组件：
 * - 统计指标（StatCard / StatGrid）
 * - 状态切换（StateView 及配套骨架）
 * - 入场动效（FadeInUp / StaggeredList / ScrollReveal / InteractivePress）
 * - 引导微动效（AttentionPulse / NewBadge / InteractiveHint）
 *
 * 📋 三层组件约定 (ADR 003, 2026-05-14):
 *   层 1: components/ui/         shadcn 原子 (button / input / dialog / ...)
 *   层 2: components/ui-unified/ 业务复合 (本目录, 新组件首选放这里)
 *   层 3: components/common/     ⚠️ deprecated, 4 个历史组件渐进迁出
 *
 * 设计约束（DesignDNA §14 合规协议）：
 * - 所有色值走语义 CSS 变量，保留琥珀暖橙主题
 * - 字重仅使用 400 / 500 / 600（index.css 已对 bold/extrabold/black 做向下兼容）
 * - 圆角使用 rounded-dd_* / rounded-pill 系列
 * - 阴影使用 shadow-elev-0..5 电梯体系
 * - 动效使用 var(--ease-standard) / var(--ease-decelerate) / var(--ease-spring)
 *
 * 配套：
 * - @/components/ai-primitives     — AI/Agent 领域原子
 * - @/components/responsive         — 响应式原语（ScrollShell / SplitView）
 * - @/components/common             — ⚠️ deprecated, 见 ADR 003
 */

export { StatCard, StatGrid } from './StatCard'
export type { StatCardProps } from './StatCard'

export {
  StateView,
  DefaultLoadingSkeleton,
  StatCardSkeleton,
  TableSkeleton,
  InlineLoader,
} from './StateView'
export type { PageState } from './StateView'

export { FadeInUp, StaggeredList, ScrollReveal, InteractivePress } from './Motion'

export { AttentionPulse, NewBadge, InteractiveHint } from './Guidance'

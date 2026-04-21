/**
 * AI Primitives — 安心法务 AI/Agent 场景原子组件
 *
 * 使用约束（DesignDNA §14 合规协议）：
 * - 所有样式 token 来自 DESIGN.md / index.css CSS 变量
 * - 禁止硬编码颜色；禁止混用其他图标库
 * - 必须支持暗色模式（基于语义 token 自动切换）
 *
 * 参考原型：Claude（编辑器暖感）× Linear（工具精度）× Cursor（差异视图）
 */

export { ThinkingChain } from './ThinkingChain'
export type { ThinkingStep, ThinkingStepStatus } from './ThinkingChain'

export { CitationPill } from './CitationPill'
export type { CitationSource } from './CitationPill'

export { ConfidenceBadge } from './ConfidenceBadge'
export type { ConfidenceLevel } from './ConfidenceBadge'

export { RiskHighlight } from './RiskHighlight'
export type { RiskLevel } from './RiskHighlight'

export { A2UIBoundary } from './A2UIBoundary'

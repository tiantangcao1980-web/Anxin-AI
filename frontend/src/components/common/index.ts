/**
 * ⚠️ DEPRECATED (2026-05-14, ADR 003): components/common/ 整体逐步迁出
 *
 * - 新组件**不再放本目录**, 改放 components/ui-unified/
 * - 现有 4 个组件 (EmptyState / LoadingState / ErrorState / PagePlaceholder)
 *   保持向后兼容, 但下一里程碑 PR 会逐个迁移到 ui-unified/
 * - 见 docs/adr/003-ui-components-three-tier-hierarchy.md 完整方案
 */
export { EmptyState } from './EmptyState'
export { LoadingState } from './LoadingState'
export { ErrorState } from './ErrorState'
export { PagePlaceholder } from './PagePlaceholder'

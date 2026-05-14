/**
 * ⚠️ DEPRECATED (2026-05-14, Phase J / ADR 003 Phase 2):
 *
 * 4 个组件已**物理迁入** components/ui-unified/. 本 index.ts 仅作为
 * **deprecation alias** 提供 1 个 release 周期的向后兼容. 下一里程碑 PR 会:
 *   1. 全仓 grep `from '@/components/common'` 改为 `from '@/components/ui-unified'`
 *   2. 删除本目录 (含 index.ts)
 *
 * 新代码请直接从 `@/components/ui-unified` 导入. 见
 * docs/adr/003-ui-components-three-tier-hierarchy.md 完整方案.
 */

export {
  EmptyState,
  LoadingState,
  ErrorState,
  PagePlaceholder,
} from '@/components/ui-unified'

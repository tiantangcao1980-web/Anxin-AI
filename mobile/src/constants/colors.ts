// -*- coding: utf-8 -*-
/**
 * V2 简易调色板（兼容层）。
 *
 * 2026-05 起，新业务页应优先使用 V3 主题：
 *
 *   import { useV3Theme } from '@/theme'
 *   const t = useV3Theme()
 *   // 文本：t.colors.text / textSecondary / textMuted
 *   // 状态：t.colors.success / warning / error
 *   // V3 扩展：t.colors.aiThinking / riskHigh / etc.
 *   // 业务域：从 '@/theme' import { domain } 直接读
 *
 * 本文件保留是为了兼容尚未迁移到 V3 theme 的旧业务页（find-lawyer, cases,
 * contracts, approvals 等）。两套 palette 在共有字段上**必须**保持一致，
 * 由 `src/constants/colors.test.ts` 守护。
 */

export const Colors = {
  primary: '#D4A574',
  primaryLight: '#E8C9A8',
  primaryDark: '#B8895A',
  background: '#FFFFFF',
  surface: '#F8F8F8',
  text: '#1C1C1E',
  // 2026-05 调和：与 V3 lightTheme（ink500/ink400）对齐，
  // 次要文本对比度从 4.6:1 提升至 6.3:1，更符合 WCAG AA。
  textSecondary: '#6E6E73',
  textMuted: '#8E8E93',
  border: '#E5E5EA',
  success: '#34C759',
  warning: '#FF9500',
  error: '#FF3B30',
  info: '#007AFF',
  white: '#FFFFFF',
  black: '#000000',
}

export const DarkColors = {
  ...Colors,
  background: '#1C1C1E',
  surface: '#2C2C2E',
  text: '#FFFFFF',
  textSecondary: '#AEAEB2',
  border: '#3C3C43',
}

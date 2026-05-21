// -*- coding: utf-8 -*-
/**
 * V2 简易调色板（兼容层）。已对齐飞书风蓝图（2026-05-22）：brand 用 #F97316 琥珀橙。
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
  primary: '#F97316',
  primaryLight: '#FDBA74',
  primaryDark: '#EA580C',
  imPrimary: '#1664FF',
  background: '#FFFFFF',
  // 与 V3 palette/lightTheme 共有字段保持一致（colors.test.ts 守护）
  surface: '#FAF8F6',
  text: '#1C1A17',
  textSecondary: '#7A736D',
  textMuted: '#9A938D',
  border: '#E8E5E0',
  success: '#16A34A',
  warning: '#F59E0B',
  error: '#DC2626',
  info: '#3B82F6',
  white: '#FFFFFF',
  black: '#000000',
}

export const DarkColors = {
  ...Colors,
  background: '#0F0F11',
  surface: '#1C1C1E',
  text: '#FFFFFF',
  textSecondary: '#AEAEB2',
  border: '#3C3C43',
}

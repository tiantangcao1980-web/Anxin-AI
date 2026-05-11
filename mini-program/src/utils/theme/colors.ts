// -*- coding: utf-8 -*-
/**
 * V3 设计令牌：颜色（与 web/mobile 端 design tokens 对齐）
 *
 * 暖色主色调 (warmth & trust) — 参考 feedback_ui_redesign 与 mobile/src/theme/tokens.ts。
 * 同时供 Sass / TS 双向消费：
 *   - .scss 通过 `@import` 不可读 ts，因此 app.scss 复制了一份；
 *   - .tsx 直接 `import { palette } from '@/utils/theme/colors'` 用于内联样式。
 */

export const palette = {
  // 主色：温暖的赤茶 / 焦糖 / 沙金
  primary: '#D4A574',
  primaryDark: '#B8864E',
  primaryLight: '#E8C9A8',
  primarySoft: '#FBF3E8',

  // 中性色
  ink900: '#1D2129',
  ink700: '#4E5969',
  ink500: '#86909C',
  ink300: '#C9CDD4',
  ink100: '#E5E6EB',

  // 背景
  bg: '#FAFAFA',
  surface: '#FFFFFF',
  surfaceMuted: '#F5F5F5',

  // 状态
  success: '#22C55E',
  warning: '#F59E0B',
  danger: '#EF4444',
  info: '#3B82F6',

  // 边框 / 分割
  border: '#EEEEEE',
  divider: '#F0F0F0',
} as const

/** 业务域 → 主题色（4 大分组） */
export const domainPalette = {
  '综合协调': '#D4A574', // 暖金
  '合规经营': '#5C7CFA', // 蓝
  '增长获客': '#22C55E', // 绿
  '出海跨境': '#F97316', // 橙
} as const

export type Palette = typeof palette
export type DomainPalette = typeof domainPalette

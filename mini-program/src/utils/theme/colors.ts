// -*- coding: utf-8 -*-
/**
 * V3 设计令牌：颜色（飞书风 — 2026-05-22 对齐）
 *
 * Brand 用琥珀橙 #F97316（与 web/mobile/desktop 一致）；
 * IM 沟通色用飞书蓝 #1664FF；
 * 中性色采用暖灰系，与 mobile/src/theme/colors.ts 同步。
 *
 * SCSS 端见 mini-program/src/styles/design-tokens.scss；
 * TSX 端 `import { palette } from '@/utils/theme/colors'`。
 */

export const palette = {
  // 主色：琥珀橙
  primary: '#F97316',
  primaryDark: '#EA580C',
  primaryLight: '#FDBA74',
  primarySoft: '#FFF7ED',

  // IM 蓝（飞书风）
  imPrimary: '#1664FF',
  imPrimaryDark: '#003FB3',
  imPrimaryLight: '#5C91FF',
  imPrimarySoft: '#EBF2FF',

  // 中性色（暖灰）
  ink900: '#1C1A17',
  ink700: '#3C3A35',
  ink500: '#7A736D',
  ink300: '#AEAEB2',
  ink100: '#E8E5E0',

  // 背景
  bg: '#FAF8F6',
  surface: '#FFFFFF',
  surfaceMuted: '#F5F4F0',

  // 状态
  success: '#16A34A',
  warning: '#F59E0B',
  danger: '#DC2626',
  info: '#3B82F6',

  // 边框 / 分割
  border: '#E8E5E0',
  divider: '#F0EEEA',
} as const

/** 业务域 → 主题色（4 大分组） */
export const domainPalette = {
  '综合协调': '#F97316', // 品牌橙
  '合规经营': '#1664FF', // 飞书蓝
  '增长获客': '#16A34A', // 成功绿
  '出海跨境': '#7C5CFF', // AI 紫
} as const

export type Palette = typeof palette
export type DomainPalette = typeof domainPalette

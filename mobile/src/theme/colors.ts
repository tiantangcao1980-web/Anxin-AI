// -*- coding: utf-8 -*-
/**
 * V3 颜色令牌（飞书 / 企微对标版 — 2026-05-22）。
 *
 * 设计基调：暖橙品牌色 (#F97316) + 飞书蓝沟通色 (#1664FF) + 暖灰中性背景。
 * Brand 用于 CTA / 激活态 / 品牌徽章；IM Blue 用于消息高亮 / 链接 / @ 提及 / 在线状态。
 *
 * 与 frontend/src/index.css 和 DESIGN.md §10.11 token contract 一致。
 */

export const palette = {
  // ===== 品牌琥珀橙（与 Web --primary 对齐） =====
  primary: '#F97316',
  primary50: '#FFF7ED',
  primary100: '#FFEDD5',
  primary200: '#FED7AA',
  primary300: '#FDBA74',
  primary400: '#FB923C',
  primary500: '#F97316',
  primary600: '#EA580C',
  primary700: '#C2410C',
  primary800: '#9A3412',
  primary900: '#7C2D12',

  // ===== IM 蓝（飞书风沟通色） =====
  imPrimary: '#1664FF',
  imPrimary50: '#EBF2FF',
  imPrimary100: '#D6E4FF',
  imPrimary200: '#ADC8FF',
  imPrimary300: '#85ADFF',
  imPrimary400: '#5C91FF',
  imPrimary500: '#1664FF',
  imPrimary600: '#0050E6',
  imPrimary700: '#003FB3',

  // ===== 中性 =====
  ink900: '#1C1A17',
  ink800: '#2C2A26',
  ink700: '#3C3A35',
  ink600: '#4D4A45',
  ink500: '#7A736D',
  ink400: '#9A938D',
  ink300: '#AEAEB2',
  ink200: '#D1D1D6',
  ink100: '#E8E5E0',
  ink50: '#FAF8F6',

  // ===== 表面 =====
  bg: '#FFFFFF',
  bgMuted: '#FAF8F6',
  surface1: '#FFFFFF',
  surface2: '#FAF8F6',
  border: '#E8E5E0',
  borderSoft: 'rgba(232,229,224,0.6)',

  // ===== 状态色 =====
  success: '#16A34A',
  successSoft: '#E8F6EE',
  warning: '#F59E0B',
  warningSoft: '#FFF4E0',
  error: '#DC2626',
  errorSoft: '#FFE5E5',
  info: '#3B82F6',
  infoSoft: '#E0EDFF',

  // ===== AI 强调 =====
  ai: '#7C5CFF',
  aiSurface: 'rgba(124,92,255,0.08)',

  // ===== AI 专属语义 (V3 — 与 frontend --ai-thinking/suggestion/citation 对齐) =====
  aiThinking: '#A78BFA',
  aiThinkingSurface: 'rgba(167,139,250,0.10)',
  aiSuggestion: '#34A853',
  aiSuggestionSurface: 'rgba(52,168,83,0.10)',
  aiCitation: '#3F8FE0',
  aiCitationSurface: 'rgba(63,143,224,0.10)',

  // ===== 风险三档（与 frontend --risk-* 对齐） =====
  riskHigh: '#E04848',
  riskHighSoft: '#FBECEC',
  riskMedium: '#E2A311',
  riskMediumSoft: '#FCF3DA',
  riskLow: '#8E867D',
  riskLowSoft: '#F2EFEA',

  // ===== 置信度三档 =====
  confidenceHigh: '#2F9E5C',
  confidenceMedium: '#E2A311',
  confidenceLow: '#8E867D',
} as const

// 2026-05 Reset: 删除 8 个 domain.* 高饱和色（含被 ui-design FORBIDDEN COLORS 命中的紫色）。
// 业务域元数据（id / labelZh / labelEn）改为 metaOnly 形式，不带 color/surface：
export const domainMeta = {
  legal:      { labelZh: '法务',     labelEn: 'Legal' },
  finance:    { labelZh: '财务',     labelEn: 'Finance' },
  tax:        { labelZh: '税务',     labelEn: 'Tax' },
  compliance: { labelZh: '合规',     labelEn: 'Compliance' },
  operations: { labelZh: '经营管理', labelEn: 'Operations' },
  growth:     { labelZh: '调研获客', labelEn: 'Growth' },
  content:    { labelZh: '内容产出', labelEn: 'Content' },
  global:     { labelZh: '出海跨境', labelEn: 'Global' },
} as const

export type DomainId = keyof typeof domainMeta

export interface ThemeColors {
  primary: string
  primary50: string
  primary100: string
  primary200: string
  primary300: string
  primary400: string
  primary500: string
  primary600: string
  primary700: string
  primary800: string
  primary900: string
  imPrimary: string
  imPrimary50: string
  imPrimary100: string
  imPrimary200: string
  imPrimary300: string
  imPrimary400: string
  imPrimary500: string
  imPrimary600: string
  imPrimary700: string
  ink900: string
  ink800: string
  ink700: string
  ink600: string
  ink500: string
  ink400: string
  ink300: string
  ink200: string
  ink100: string
  ink50: string
  bg: string
  bgMuted: string
  surface1: string
  surface2: string
  borderSoft: string
  success: string
  successSoft: string
  warning: string
  warningSoft: string
  error: string
  errorSoft: string
  info: string
  infoSoft: string
  ai: string
  aiSurface: string
  // V3 新增：AI 语义 + 风险三档 + 置信度
  aiThinking: string
  aiThinkingSurface: string
  aiSuggestion: string
  aiSuggestionSurface: string
  aiCitation: string
  aiCitationSurface: string
  riskHigh: string
  riskHighSoft: string
  riskMedium: string
  riskMediumSoft: string
  riskLow: string
  riskLowSoft: string
  confidenceHigh: string
  confidenceMedium: string
  confidenceLow: string
  // 主题专用
  background: string
  backgroundMuted: string
  surface: string
  surfaceMuted: string
  text: string
  textSecondary: string
  textMuted: string
  border: string
  divider: string
  shadow: string
}

export const lightTheme: ThemeColors = {
  ...palette,
  background: palette.bg,
  backgroundMuted: palette.bgMuted,
  surface: palette.surface1,
  surfaceMuted: palette.surface2,
  text: palette.ink900,
  textSecondary: palette.ink500,
  textMuted: palette.ink400,
  border: palette.border,
  divider: palette.ink100,
  shadow: 'rgba(28,26,23,0.06)',
}

export const darkTheme: ThemeColors = {
  ...palette,
  background: '#0F0F11',
  backgroundMuted: '#171719',
  surface: '#1C1C1E',
  surfaceMuted: '#2C2C2E',
  text: '#FFFFFF',
  textSecondary: '#C7C7CC',
  textMuted: '#8E8E93',
  border: '#3C3C43',
  divider: '#2C2C2E',
  shadow: 'rgba(0,0,0,0.5)',
}

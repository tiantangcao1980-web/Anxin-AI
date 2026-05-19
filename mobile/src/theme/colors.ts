// -*- coding: utf-8 -*-
/**
 * V3 颜色令牌（与 frontend/src/lib/design-tokens.ts 对齐）。
 *
 * 设计基调：暖色主色调（#D4A574 古铜驼）+ 中性灰阶背景，参考
 * 苹果/影石/Linear/Stripe 的克制企业级语言，无蓝紫渐变 / 无 AI 味。
 *
 * 与现有 src/constants/colors.ts 共存：constants/colors 是 V2 简易调色板，
 * V3 业务页统一从 `@/theme` 导入；老页面尚未迁移时仍可用旧文件。
 */

export const palette = {
  // ===== 主色（暖色驼黄系） =====
  primary: '#D4A574',
  primary50: '#FAF3EA',
  primary100: '#F2E3CC',
  primary200: '#E8C9A8',
  primary300: '#DDAF82',
  primary400: '#D4A574',
  primary500: '#C18C56',
  primary600: '#B8895A',
  primary700: '#996F44',
  primary800: '#7A5734',
  primary900: '#5C4126',

  // ===== 中性 =====
  ink900: '#1C1C1E',
  ink800: '#2C2C2E',
  ink700: '#3C3C43',
  ink600: '#4D4D52',
  ink500: '#6E6E73',
  ink400: '#8E8E93',
  ink300: '#AEAEB2',
  ink200: '#D1D1D6',
  ink100: '#E5E5EA',
  ink50: '#F2F2F7',

  // ===== 表面 =====
  bg: '#FFFFFF',
  bgMuted: '#F8F8FA',
  surface1: '#FFFFFF',
  surface2: '#F2F2F7',
  border: '#E5E5EA',
  borderSoft: 'rgba(229,229,234,0.6)',

  // ===== 状态色 =====
  success: '#34C759',
  successSoft: '#E6F8EC',
  warning: '#FF9500',
  warningSoft: '#FFF1DC',
  error: '#FF3B30',
  errorSoft: '#FFE5E3',
  info: '#007AFF',
  infoSoft: '#E0EFFF',

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
  // 复制 palette 的所有 key 但放宽为 string，使 light/dark 可互替
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
  shadow: 'rgba(28,28,30,0.06)',
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

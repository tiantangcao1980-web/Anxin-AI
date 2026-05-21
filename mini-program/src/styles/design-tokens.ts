// Keep runtime configuration colors aligned with design-tokens.scss.
// Taro app.config.ts cannot read SCSS variables at build time, so the small
// set of config-level color tokens lives here.
//
// V3 (2026-05): 新增风险三档 + AI 语义 + 8 大业务域，
// 与 frontend/mobile 跨端对齐。详见 docs/design/ui-audit-and-upgrade-2026-05.md

export const miniProgramTheme = {
  brandPrimary: '#D4A574',
  brandPrimaryDark: '#B8864E',
  background: '#FAF8F5',
  surface: '#FFFFFF',
  textPrimary: '#1C1A18',
  textSecondary: '#5F564E',
  textTertiary: '#8E867D',
  border: '#E5E0DA',
} as const

// ===== 风险三档（V3 — 跨端统一） =====
export const riskTier = {
  high:   { color: '#E04848', surface: '#FBECEC', labelZh: '高风险' },
  medium: { color: '#E2A311', surface: '#FCF3DA', labelZh: '中风险' },
  low:    { color: '#8E867D', surface: '#F2EFEA', labelZh: '低风险' },
} as const
export type RiskTier = keyof typeof riskTier

// ===== AI 语义色 =====
export const aiSemantic = {
  thinking:   { color: '#A78BFA', surface: 'rgba(167,139,250,0.10)' },
  suggestion: { color: '#34A853', surface: 'rgba(52,168,83,0.10)' },
  citation:   { color: '#3F8FE0', surface: 'rgba(63,143,224,0.10)' },
} as const

// 2026-05 Reset: 删除 8 个 domain.* 高饱和色（含被 ui-design FORBIDDEN COLORS 命中的紫色）。
// 仅保留业务域元数据，不带 color/surface 字段。
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

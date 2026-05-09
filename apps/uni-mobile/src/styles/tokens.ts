export const touch = {
  minTargetPx: 44,
  minTargetRpx: 88,
} as const

export const spacing = {
  pageRpx: 32,
  sectionRpx: 32,
  cardRpx: 28,
  controlGapRpx: 16,
} as const

export const radius = {
  cardRpx: 16,
  controlRpx: 12,
  badgeRpx: 8,
} as const

export const safeArea = {
  bottom: 'env(safe-area-inset-bottom)',
  top: 'env(safe-area-inset-top)',
} as const

export const color = {
  background: '#F7F8FA',
  surface: '#FFFFFF',
  textPrimary: '#111827',
  textSecondary: '#5F6673',
  border: '#D8DEE8',
  primary: '#2563EB',
  success: '#15803D',
  warning: '#B45309',
  danger: '#DC2626',
} as const

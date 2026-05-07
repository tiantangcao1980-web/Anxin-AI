// Keep runtime configuration colors aligned with design-tokens.scss.
// Taro app.config.ts cannot read SCSS variables at build time, so the small
// set of config-level color tokens lives here.

export const miniProgramTheme = {
  brandPrimary: '#D4A574',
  background: '#F5F5F5',
  surface: '#ffffff',
  textTertiary: '#999999',
} as const

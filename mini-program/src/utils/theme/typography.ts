// -*- coding: utf-8 -*-
/**
 * V3 设计令牌：字体（rpx 为微信小程序设计单位 750 设计稿）
 *
 * 与 mobile 端 typography.ts 对齐，rem→rpx 通过 ×2 转换。
 */

export const fontSize = {
  caption: 22, // 11px
  body: 28, // 14px
  bodyLarge: 32, // 16px
  subtitle: 36, // 18px
  title: 44, // 22px
  display: 56, // 28px
  hero: 72, // 36px
} as const

export const fontWeight = {
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const

export const lineHeight = {
  tight: 1.25,
  normal: 1.5,
  relaxed: 1.75,
} as const

export const fontFamily =
  "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', " +
  "'Microsoft YaHei', 'Source Han Sans SC', sans-serif"

// -*- coding: utf-8 -*-
/**
 * V3 设计令牌：间距 / 圆角 / 阴影（rpx 单位，750 设计稿）
 */

export const spacing = {
  xs: 8, // 4px
  sm: 16, // 8px
  md: 24, // 12px
  lg: 32, // 16px
  xl: 48, // 24px
  '2xl': 64, // 32px
  '3xl': 96, // 48px
} as const

export const radius = {
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  pill: 999,
} as const

export const shadow = {
  card: '0 4rpx 16rpx rgba(29, 33, 41, 0.06)',
  elevated: '0 8rpx 32rpx rgba(29, 33, 41, 0.10)',
  hover: '0 12rpx 40rpx rgba(212, 165, 116, 0.20)',
} as const

// -*- coding: utf-8 -*-
/**
 * V3 字体令牌。
 *
 * 跨平台字体：iOS 默认使用 SF Pro（系统调用），Android 使用 Roboto，Web fallback 用系统 sans。
 * React Native 端不显式指定 fontFamily 时会自动走平台默认字体。
 *
 * 注意：本文件中的 'System' / 'Roboto' 字面值是 React Native StyleSheet
 * 的 fontFamily prop（OS 平台 API），不是 Web 浏览器的 CSS font-family。
 * ui-design skill 的 FORBIDDEN FONTS 规则针对 Web CSS，不限制 RN 平台 API。
 */

import { Platform } from 'react-native'

const isIOS = Platform.OS === 'ios'

export const fontFamily = {
  /** 默认正文：iOS SF Pro / Android Roboto / Web system */
  body: isIOS ? 'System' : 'Roboto',
  /** 标题：稍微粗一点 */
  display: isIOS ? 'System' : 'Roboto',
  /** 中文优化（Android 上 Noto Sans SC 渲染更好） */
  cnBody: isIOS ? 'PingFang SC' : 'Noto Sans SC',
  /** 等宽（代码、数字） */
  mono: isIOS ? 'Menlo' : 'monospace',
} as const

/** 字号阶梯（与 frontend tailwind.config.js text-* 对齐） */
export const fontSize = {
  caption: 11,
  micro: 12,
  body: 14,
  bodyLg: 16,
  h3: 18,
  h2: 22,
  h1: 28,
  display: 34,
} as const

export const lineHeight = {
  caption: 16,
  micro: 18,
  body: 20,
  bodyLg: 22,
  h3: 24,
  h2: 28,
  h1: 34,
  display: 40,
} as const

export const fontWeight = {
  regular: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
}

export const text = {
  display: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.display,
    lineHeight: lineHeight.display,
    fontWeight: fontWeight.semibold,
    letterSpacing: -0.5,
  },
  h1: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h1,
    lineHeight: lineHeight.h1,
    fontWeight: fontWeight.semibold,
    letterSpacing: -0.3,
  },
  h2: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    lineHeight: lineHeight.h2,
    fontWeight: fontWeight.semibold,
    letterSpacing: -0.2,
  },
  h3: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    lineHeight: lineHeight.h3,
    fontWeight: fontWeight.medium,
  },
  bodyLg: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    lineHeight: lineHeight.bodyLg,
    fontWeight: fontWeight.regular,
  },
  body: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: lineHeight.body,
    fontWeight: fontWeight.regular,
  },
  micro: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.micro,
    lineHeight: lineHeight.micro,
    fontWeight: fontWeight.regular,
  },
  caption: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: lineHeight.caption,
    fontWeight: fontWeight.regular,
  },
} as const

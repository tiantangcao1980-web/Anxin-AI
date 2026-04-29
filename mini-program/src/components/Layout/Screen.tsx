// -*- coding: utf-8 -*-
/**
 * Screen 容器 —— 全屏页面包裹
 *
 * 职责：
 *   - 统一背景色 / 安全区适配
 *   - 提供 padded 选项控制内边距
 *   - 暴露 navHeight 占位（需要时业务页自取）
 */

import { ReactNode } from 'react'
import { View } from '@tarojs/components'
import './Screen.scss'

interface ScreenProps {
  children: ReactNode
  className?: string
  /** 是否给左右内边距，默认 true */
  padded?: boolean
  /** 自定义背景色（默认主题 bg） */
  backgroundColor?: string
}

export default function Screen(props: ScreenProps) {
  const { children, className = '', padded = true, backgroundColor } = props
  const cls = [
    'anxin-screen',
    padded ? 'anxin-screen--padded' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')
  const style = backgroundColor ? `background-color: ${backgroundColor};` : ''
  return (
    <View className={cls} style={style}>
      {children}
    </View>
  )
}

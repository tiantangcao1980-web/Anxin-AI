// -*- coding: utf-8 -*-
import { PropsWithChildren, useEffect } from 'react'
import Taro, { useLaunch } from '@tarojs/taro'
import { tokenStorage } from './utils/auth/token'
import './app.scss'

/**
 * App 根组件（V3 P21-A）
 *
 * 职责：
 *   - 启动时检查 token —— 未登录直接跳 /pages/login
 *     （tabBar 页面无法 redirectTo，因此用 reLaunch）
 *   - 监听微信小程序 onShow / onHide 生命周期（Taro 用 useLaunch）
 *   - 全局错误兜底 —— 后续 P21-B/C/D 接入 toast 反馈
 */

function App({ children }: PropsWithChildren) {
  useLaunch(() => {
    // 启动埋点占位
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.log('[anxin] mini-program launched')
    }
  })

  useEffect(() => {
    // 未登录 → 强制跳登录页（避开 launch 时机过早问题）
    if (!tokenStorage.isAuthenticated()) {
      Taro.reLaunch({ url: '/pages/login/index' }).catch(() => {
        // 已经在 login 页时会失败，可忽略
      })
    }
  }, [])

  return children
}

export default App

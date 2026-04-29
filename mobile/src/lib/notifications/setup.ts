// -*- coding: utf-8 -*-
/**
 * 一键初始化推送：注册 + 绑定前台 / 后台 handler。
 *
 * 在 `app/_layout.tsx` 的 useEffect 里调用一次即可。
 */

import { registerForPushNotificationsAsync } from './register'
import {
  bindForegroundHandler,
  bindNotificationResponseHandler,
  defaultTaskNotificationDispatcher,
} from './handler'
import type { PushTokenRegisterResult } from '../types'

export interface SetupResult {
  registration: PushTokenRegisterResult | null
  /** 解绑回调，组件 unmount 时调用 */
  unsubscribe: () => void
}

export async function setupV3PushNotifications(options: {
  onForeground?: (payload: unknown) => void
  onResponse?: (payload: unknown) => void
} = {}): Promise<SetupResult> {
  const registration = await registerForPushNotificationsAsync()
  const unsubFg = await bindForegroundHandler(options.onForeground ?? (() => {}))
  const unsubResp = await bindNotificationResponseHandler(
    options.onResponse ?? defaultTaskNotificationDispatcher,
  )
  return {
    registration,
    unsubscribe: () => {
      unsubFg()
      unsubResp()
    },
  }
}

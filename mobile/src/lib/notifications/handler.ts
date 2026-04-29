// -*- coding: utf-8 -*-
/**
 * 推送处理 / 路由 dispatcher（V3）。
 *
 * - 前台收到推送：触发 onForeground（业务可拿来刷列表 / 显示 in-app banner）
 * - 用户点击推送：根据 payload.type 跳转到对应业务页面
 *   * agent_task_done / failed / needs_approval -> /(tabs)/tasks/[id]
 */

import { router } from 'expo-router'
import type { TaskNotificationPayload } from '../types'

interface OptionalDeps {
  Notifications: any
}

async function loadOptionalDeps(): Promise<OptionalDeps | null> {
  try {
    const Notifications = await import('expo-notifications').catch(() => null)
    if (!Notifications) return null
    return { Notifications }
  } catch {
    return null
  }
}

export async function bindForegroundHandler(
  handler: (payload: unknown) => void,
): Promise<() => void> {
  const deps = await loadOptionalDeps()
  if (!deps) return () => {}
  const sub = deps.Notifications.addNotificationReceivedListener((notification: any) => {
    handler(notification?.request?.content?.data ?? {})
  })
  return () => sub.remove()
}

export async function bindNotificationResponseHandler(
  handler: (payload: unknown) => void,
): Promise<() => void> {
  const deps = await loadOptionalDeps()
  if (!deps) return () => {}
  const sub = deps.Notifications.addNotificationResponseReceivedListener((response: any) => {
    handler(response?.notification?.request?.content?.data ?? {})
  })
  return () => sub.remove()
}

/**
 * 默认 dispatcher：根据 payload.type 把用户送到对应路由。
 * 未识别的类型不跳转，业务可在 setup 里换成自己的 dispatcher。
 */
export function defaultTaskNotificationDispatcher(payload: unknown) {
  if (!payload || typeof payload !== 'object') return
  const data = payload as Partial<TaskNotificationPayload>
  if (!data.type) return
  switch (data.type) {
    case 'agent_task_done':
    case 'agent_task_failed':
    case 'agent_task_needs_approval':
      if (data.task_id) {
        // expo-router push 接受字符串路径
        router.push(`/(tabs)/tasks/${encodeURIComponent(data.task_id)}` as any)
      }
      return
    default:
      return
  }
}

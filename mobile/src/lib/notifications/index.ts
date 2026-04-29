// -*- coding: utf-8 -*-
/**
 * V3 移动端推送通知模块。
 *
 * 包装 `expo-notifications` + 后端 `/notifications/devices/register` 上报，
 * 任务事件 deep-link 跳转到 `/(tabs)/tasks/[id]`。
 *
 * 与老的 `src/lib/push-notifications.ts` 共存：
 *   - 老模块走 `/notifications/push-tokens`
 *   - V3 走 `/notifications/devices/register`，并增加任务通知路由 dispatcher
 *
 * 接入方式（`app/_layout.tsx`）：
 *
 *   useEffect(() => {
 *     setupV3PushNotifications().then(({ subscriptions }) => {
 *       return () => subscriptions.forEach(sub => sub())
 *     })
 *   }, [])
 */

export * from './register'
export * from './handler'
export * from './setup'

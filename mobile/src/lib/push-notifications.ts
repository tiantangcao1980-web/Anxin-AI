/**
 * 推送通知接入（Expo Notifications）。
 *
 * 初始化流程：
 * 1. 冷启动时调用 `registerForPushNotifications`
 * 2. 请求权限（首次）并拿到 Expo Push Token
 * 3. 上报到后端 `POST /api/v1/notifications/push-tokens`，绑定到当前账号
 * 4. 监听前台 / 后台 / 点击三种事件，转发到对应路由
 *
 * 注意：
 * - Expo Go 从 SDK 53 起不再支持远程推送；生产版需 EAS Build
 * - 依赖未在 package.json 注册时会 `require` 失败，本模块做 soft import
 */

import { Platform } from 'react-native'
import Constants from 'expo-constants'
import { api } from '../services/api'

export interface PushRegistrationResult {
  success: boolean
  token?: string
  reason?: string
}

/**
 * Soft-import `expo-notifications` & `expo-device` —— 未安装依赖时不抛错，返回 success=false。
 * 这让项目启动期不强依赖，方便 CI lint 通过；真正推送接入时再 pnpm add。
 */
async function loadOptionalDeps(): Promise<
  | {
      Notifications: any
      Device: any
    }
  | null
> {
  try {
    // @ts-ignore - 允许未安装
    const Notifications = await import('expo-notifications').catch(() => null)
    // @ts-ignore
    const Device = await import('expo-device').catch(() => null)
    if (!Notifications || !Device) return null
    return { Notifications, Device }
  } catch {
    return null
  }
}

/**
 * 注册远程推送。返回 token 字符串或 null。
 *
 * 调用方（通常在 `_layout.tsx` 或进入 tabs 后）：
 *   const result = await registerForPushNotifications()
 *   if (result.success) console.log('push token:', result.token)
 */
export async function registerForPushNotifications(): Promise<PushRegistrationResult> {
  const deps = await loadOptionalDeps()
  if (!deps) {
    return {
      success: false,
      reason: 'expo-notifications 未安装；请 `pnpm add expo-notifications expo-device`',
    }
  }

  const { Notifications, Device } = deps

  // 模拟器 / 未授权硬件：Expo 官方建议不注册
  if (!Device.isDevice) {
    return { success: false, reason: '模拟器不支持远程推送' }
  }

  const { status: existing } = await Notifications.getPermissionsAsync()
  let status = existing
  if (existing !== 'granted') {
    const req = await Notifications.requestPermissionsAsync()
    status = req.status
  }
  if (status !== 'granted') {
    return { success: false, reason: '用户未授权推送' }
  }

  const projectId = Constants.expoConfig?.extra?.eas?.projectId
  const tokenData = projectId
    ? await Notifications.getExpoPushTokenAsync({ projectId })
    : await Notifications.getExpoPushTokenAsync()
  const token: string = tokenData.data

  // Android 需要设置默认 channel
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.DEFAULT,
      lightColor: '#D4A574',
    })
  }

  // 上报到后端
  try {
    await api.post('/notifications/push-tokens', {
      token,
      platform: Platform.OS,
      device_id: Constants.sessionId ?? 'unknown',
    })
  } catch (err) {
    // 上报失败不阻塞；token 仍可缓存到本地
    console.warn('[push] 上报 token 到后端失败', err)
  }

  return { success: true, token }
}

/**
 * 绑定前台消息监听：收到推送时把 payload 交给 handler（例如刷新列表、更新徽章）。
 * 返回解绑函数。
 */
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

/**
 * 绑定点击打开通知的处理：通常用 deep link 把用户送到对应业务页。
 */
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

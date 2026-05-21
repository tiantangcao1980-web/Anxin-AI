// -*- coding: utf-8 -*-
/**
 * 推送 token 注册（V3）。
 *
 * 使用 soft-import 避免 `expo-notifications` / `expo-device` 未安装时启动失败。
 * 拿到 ExpoPushToken 后上报到 `POST /notifications/devices/register`。
 */

import { Platform } from 'react-native'
import Constants from 'expo-constants'
import { getApiClient } from '../api/client'
import type { PushTokenRegisterResult } from '../types'

interface RegisterOptions {
  /** 显式覆盖后端注册端点，便于过渡期 mock */
  endpoint?: string
}

interface OptionalDeps {
  Notifications: any
  Device: any
}

async function loadOptionalDeps(): Promise<OptionalDeps | null> {
  try {
    const Notifications = await import('expo-notifications').catch(() => null)
    const Device = await import('expo-device').catch(() => null)
    if (!Notifications || !Device) return null
    return { Notifications, Device }
  } catch {
    return null
  }
}

export async function registerForPushNotificationsAsync(
  options: RegisterOptions = {},
): Promise<PushTokenRegisterResult | null> {
  const deps = await loadOptionalDeps()
  if (!deps) {
    if (__DEV__) {
      console.warn('[push] expo-notifications / expo-device 未安装，跳过推送注册')
    }
    return null
  }

  const { Notifications, Device } = deps

  if (!Device.isDevice) {
    if (__DEV__) console.warn('[push] 模拟器不支持远程推送')
    return null
  }

  const { status: existing } = await Notifications.getPermissionsAsync()
  let status = existing
  if (existing !== 'granted') {
    const req = await Notifications.requestPermissionsAsync()
    status = req.status
  }
  if (status !== 'granted') {
    if (__DEV__) console.warn('[push] 用户未授权推送')
    return null
  }

  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ||
    Constants.easConfig?.projectId
  const tokenData = projectId
    ? await Notifications.getExpoPushTokenAsync({ projectId })
    : await Notifications.getExpoPushTokenAsync()
  const token: string = tokenData.data

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.DEFAULT,
      lightColor: '#F97316',
    })
  }

  // 上报到后端
  const endpoint = options.endpoint ?? '/notifications/devices/register'
  let pushTokenId: string | undefined
  try {
    const client = getApiClient()
    const res = await client.post(endpoint, {
      token,
      platform: Platform.OS,
      device_id: Constants.sessionId ?? `${Platform.OS}-unknown`,
      app_version: Constants.expoConfig?.version ?? '1.0.0',
    })
    pushTokenId = (res.data?.push_token_id ?? res.data?.id) as string | undefined
  } catch (err) {
    if (__DEV__) console.warn('[push] 上报后端失败（不阻塞）', err)
  }

  return {
    token,
    platform: Platform.OS as 'ios' | 'android' | 'web',
    push_token_id: pushTokenId,
  }
}

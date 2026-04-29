// -*- coding: utf-8 -*-
import { Stack } from 'expo-router'
import { Colors } from '@/constants/colors'

/**
 * 能力中心 Stack 布局 (P17-D)
 *
 * 该路由位于 (tabs)/capabilities/,但不在 BottomTab 中显式注册,
 * 以避免修改 P17-A 之外的 (tabs)/_layout.tsx — 入口通过
 * router.push('/(tabs)/capabilities') 进入(从「我的」/「协作」/外部 deeplink)。
 */
export default function CapabilitiesLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: Colors.background },
        headerTintColor: Colors.text,
        headerTitleStyle: { fontWeight: '600' },
        contentStyle: { backgroundColor: Colors.background },
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen name="index" options={{ title: '能力中心' }} />
      <Stack.Screen name="scheduled-tasks" options={{ title: '定时任务' }} />
      <Stack.Screen name="app-authorizations" options={{ title: '应用授权' }} />
      <Stack.Screen name="skills" options={{ title: '技能' }} />
      <Stack.Screen name="plugins" options={{ title: '插件' }} />
      <Stack.Screen name="message-channels" options={{ title: '消息渠道' }} />
      <Stack.Screen name="pairing-authorizations" options={{ title: '配对审批' }} />
    </Stack>
  )
}

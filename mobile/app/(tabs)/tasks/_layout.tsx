/**
 * 任务中心子路由 layout（V3 P17-B 移动端）
 *
 * 使用 Stack 让 [id] 详情页 push，并用 modal presentation 承载 new。
 * Stack 自带 swipe back gesture（iOS）—— 满足"任务详情 swipe back"。
 */
import { Stack } from 'expo-router'

import { useStackHeaderOptions } from '@/lib/theme'

export default function TasksLayout() {
  const headerOpts = useStackHeaderOptions()
  return (
    <Stack
      screenOptions={{
        ...headerOpts,
        gestureEnabled: true,
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen
        name="index"
        options={{
          title: '任务中心',
          headerShown: false, // 列表页自定义头
        }}
      />
      <Stack.Screen
        name="[id]"
        options={{
          title: '任务详情',
          headerBackTitle: '返回',
          gestureEnabled: true,
        }}
      />
      <Stack.Screen
        name="new"
        options={{
          title: '新建任务',
          presentation: 'modal',
          animation: 'slide_from_bottom',
        }}
      />
    </Stack>
  )
}

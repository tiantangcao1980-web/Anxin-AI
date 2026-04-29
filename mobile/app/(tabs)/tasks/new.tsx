/**
 * 新建任务 modal（V3 P17-B 移动端）
 *
 * Stack 设置 presentation: 'modal'，本页直接挂载 CreateTaskSheet。
 * Sheet 关闭时回退到列表（router.back）。
 */
import { useEffect, useState } from 'react'
import { StyleSheet, View } from 'react-native'
import { router } from 'expo-router'

import { CreateTaskSheet } from '@/components/v3/tasks-mobile/CreateTaskSheet'
import { useAgentTasksStore } from '@/lib/store/agentTasksStore'
import { useTheme } from '@/lib/theme'

export default function CreateTaskModalScreen() {
  const t = useTheme()
  const createTask = useAgentTasksStore((s) => s.createTask)
  const [open, setOpen] = useState(false)

  // 进入页面后立即弹出 sheet
  useEffect(() => {
    const id = setTimeout(() => setOpen(true), 50)
    return () => clearTimeout(id)
  }, [])

  return (
    <View style={[styles.container, { backgroundColor: t.background }]}>
      <CreateTaskSheet
        visible={open}
        onClose={() => {
          setOpen(false)
          // sheet 动画收起后退出 modal
          setTimeout(() => router.back(), 220)
        }}
        onSubmit={async (body) => {
          await createTask(body)
        }}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
})

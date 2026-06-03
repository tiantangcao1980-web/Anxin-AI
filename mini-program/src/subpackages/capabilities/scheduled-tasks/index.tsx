import { useEffect, useState, useCallback } from 'react'
import { View, Text, ScrollView, Switch, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
// D-3b：已接 D-1 真实后端（GET /scheduled-tasks、PUT /scheduled-tasks/{id}/toggle）。
import { scheduledTasksApi, ScheduledTask, ScheduleKind } from '../../../utils/api/scheduledTasks'
import './index.scss'

const KIND_TABS: { key: ScheduleKind; label: string; icon: string }[] = [
  { key: 'daily', label: '日常', icon: '☀️' },
  { key: 'monitor', label: '监控', icon: '🔭' },
  { key: 'report', label: '报告', icon: '📊' },
  { key: 'automation', label: '自动化', icon: '🤖' },
]

const STATUS_LABEL: Record<string, string> = {
  active: '运行中',
  paused: '已暂停',
  failed: '运行失败',
}

export default function ScheduledTasksPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [activeKind, setActiveKind] = useState<ScheduleKind>('daily')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await scheduledTasksApi.list()
      setTasks(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const onToggle = async (task: ScheduledTask, on: boolean) => {
    const next = on ? 'active' : 'paused'
    try {
      const updated = await scheduledTasksApi.toggle(task.id, next)
      setTasks((arr) => arr.map((t) => (t.id === task.id ? updated : t)))
      Taro.showToast({ title: on ? '已启用' : '已暂停', icon: 'none' })
    } catch {
      Taro.showToast({ title: '操作失败', icon: 'none' })
    }
  }

  const onCreate = () => {
    Taro.showActionSheet({
      itemList: ['每天 09:00', '每周一 09:00', '每月 1 日 10:00', '自定义 cron…'],
      success: (res) => {
        const presets = ['0 9 * * *', '0 9 * * 1', '0 10 1 * *', 'custom']
        const cron = presets[res.tapIndex]
        Taro.showToast({
          title: cron === 'custom' ? '请到 Web 端编辑 cron' : `已选择: ${cron}`,
          icon: 'none',
        })
      },
    })
  }

  const list = tasks.filter((t) => t.kind === activeKind)

  return (
    <View className='st-page'>
      {/* Tab 切换 */}
      <View className='st-tabs'>
        {KIND_TABS.map((tab) => {
          const count = tasks.filter((t) => t.kind === tab.key).length
          return (
            <View
              key={tab.key}
              className={`st-tab ${activeKind === tab.key ? 'st-tab--active' : ''}`}
              onClick={() => setActiveKind(tab.key)}
            >
              <Text className='st-tab-icon'>{tab.icon}</Text>
              <Text className='st-tab-label'>{tab.label}</Text>
              <Text className='st-tab-count'>({count})</Text>
            </View>
          )
        })}
      </View>

      <ScrollView scrollY className='st-scroll'>
        {loading ? (
          <View className='st-empty'>
            <Text className='st-empty-text'>加载中…</Text>
          </View>
        ) : list.length === 0 ? (
          <View className='st-empty'>
            <Text className='st-empty-icon'>📭</Text>
            <Text className='st-empty-text'>该分组暂无任务</Text>
          </View>
        ) : (
          list.map((task) => (
            <View key={task.id} className='st-card'>
              <View className='st-card-icon'>{task.icon}</View>
              <View className='st-card-body'>
                <View className='st-card-titlerow'>
                  <Text className='st-card-title'>{task.name}</Text>
                  <View
                    className={`st-status st-status--${task.status}`}
                  >
                    <Text className='st-status-text'>{STATUS_LABEL[task.status]}</Text>
                  </View>
                </View>
                <Text className='st-card-desc'>{task.description}</Text>
                <View className='st-card-meta'>
                  <Text className='st-card-cron'>⏱ {task.cron_human}</Text>
                  <Text className='st-card-persona'>👤 {task.agent_persona}</Text>
                </View>
              </View>
              <Switch
                className='st-switch'
                checked={task.status === 'active'}
                color='#F97316'
                onChange={(e) => onToggle(task, e.detail.value)}
              />
            </View>
          ))
        )}
        <View className='st-footer'>
          <Button className='st-create-btn' onClick={onCreate}>
            + 新建任务
          </Button>
        </View>
      </ScrollView>
    </View>
  )
}

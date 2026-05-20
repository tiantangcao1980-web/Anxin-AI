// -*- coding: utf-8 -*-
/**
 * 任务中心列表（V3 P21-B 微信小程序）
 *
 * - 顶部 3 段 segmented control：进行中 / 待审批 / 已完成
 * - ScrollView 列表，pull-to-refresh + 5s 自动轮询
 * - 任务卡片：persona emoji + 标题 + 相对时间 + status badge + 失败摘要
 * - 点击卡片 → navigateTo detail
 * - 右下角 floating CTA "+ 新建任务" → navigateTo create
 * - 空状态使用 EmptyState
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { usePullDownRefresh, useDidShow } from '@tarojs/taro'

import { Screen } from '../../components/Layout'
import EmptyState from '../../components/EmptyState'
import TaskListItem from '../../subpackages/tasks/components/TaskListItem'
import { tasksApi } from '../../subpackages/tasks/_lib/tasksApi'
import { TAB_BUCKETS, type TaskTab } from '../../subpackages/tasks/_lib/statusMap'
import type { AgentTask } from '../../types/agentTask'
import './index.scss'

const POLL_MS = 5_000

const TABS: { key: TaskTab; label: string }[] = [
  { key: 'active', label: '进行中' },
  { key: 'approval', label: '待审批' },
  { key: 'finished', label: '已完成' },
]

export default function TasksIndex() {
  const [tab, setTab] = useState<TaskTab>('active')
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const list = await tasksApi.listTasks()
      setTasks(list)
      setError(null)
    } catch (e) {
      const msg = e instanceof Error ? e.message : '加载失败'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  // 初次 + 5s 轮询
  useEffect(() => {
    void load()
    const id = setInterval(load, POLL_MS)
    return () => clearInterval(id)
  }, [load])

  useDidShow(() => {
    void load()
  })

  usePullDownRefresh(() => {
    load().finally(() => Taro.stopPullDownRefresh())
  })

  const grouped = useMemo(() => {
    const buckets: Record<TaskTab, AgentTask[]> = { active: [], approval: [], finished: [] }
    for (const t of tasks) {
      if (TAB_BUCKETS.active.includes(t.status)) buckets.active.push(t)
      else if (TAB_BUCKETS.approval.includes(t.status)) buckets.approval.push(t)
      else if (TAB_BUCKETS.finished.includes(t.status)) buckets.finished.push(t)
    }
    return buckets
  }, [tasks])

  const visible = grouped[tab]

  const goDetail = useCallback((task: AgentTask) => {
    Taro.navigateTo({ url: `/subpackages/tasks/detail/index?id=${encodeURIComponent(task.id)}` })
  }, [])

  const goCreate = useCallback(() => {
    Taro.navigateTo({ url: '/subpackages/tasks/create/index' })
  }, [])

  return (
    <Screen padded={false}>
      {/* segmented control */}
      <View className='tasks-tabs'>
        {TABS.map((t) => {
          const active = tab === t.key
          const count = grouped[t.key].length
          return (
            <View
              key={t.key}
              className={`tasks-tabs__item${active ? ' tasks-tabs__item--active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              <Text className='tasks-tabs__label'>{t.label}</Text>
              {count > 0 ? (
                <View className={`tasks-tabs__badge${active ? ' tasks-tabs__badge--active' : ''}`}>
                  <Text className='tasks-tabs__badge-text'>{count}</Text>
                </View>
              ) : null}
            </View>
          )
        })}
      </View>

      {error ? (
        <View className='tasks-error'>
          <Text className='tasks-error__text'>加载失败：{error}</Text>
          <Text className='tasks-error__retry' onClick={() => load()}>
            重试
          </Text>
        </View>
      ) : null}

      {/* 列表 */}
      <ScrollView
        className='tasks-list'
        scrollY
        enableBackToTop
        lowerThreshold={80}
        refresherEnabled={false}
      >
        {loading && tasks.length === 0 ? (
          <View className='tasks-loading'>
            <Text className='tasks-loading__text'>正在加载任务…</Text>
          </View>
        ) : visible.length === 0 ? (
          <EmptyState
            emoji={tab === 'active' ? '🗂️' : tab === 'approval' ? '🪪' : '✅'}
            title={
              tab === 'active'
                ? '没有进行中的任务'
                : tab === 'approval'
                  ? '当前没有待审批任务'
                  : '尚无已完成任务'
            }
            description={tab === 'active' ? '点击右下角 + 创建一个吧' : undefined}
            actionText={tab === 'active' ? '新建任务' : undefined}
            onAction={tab === 'active' ? goCreate : undefined}
          />
        ) : (
          <View className='tasks-list__inner'>
            {visible.map((t) => (
              <TaskListItem key={t.id} task={t} onClick={goDetail} />
            ))}
            <View className='tasks-list__footer'>
              <Text className='tasks-list__footer-text'>已加载 {visible.length} 条 · 5s 自动刷新</Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* floating CTA */}
      <View className='tasks-fab' onClick={goCreate} hoverClass='tasks-fab--hover'>
        <Text className='tasks-fab__plus'>+</Text>
        <Text className='tasks-fab__text'>新建任务</Text>
      </View>
    </Screen>
  )
}

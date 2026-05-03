// -*- coding: utf-8 -*-
/**
 * 任务详情（V3 P21-B）
 *
 * - 顶部：persona + payload + status badge
 * - 中部：Timeline (倒序 events)
 * - 底部：result 区（如有）
 * - 操作栏：
 *     running/queued/provisioning/reporting → [取消任务]
 *     needs_approval                        → [批准] [驳回（输入理由）]
 *     done/failed/cancelled                 → [重做]
 * - onShow 拉取最新 + 1s polling 实时事件流
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { View, Text, ScrollView, Input } from '@tarojs/components'
import Taro, { useDidShow, useDidHide, useRouter } from '@tarojs/taro'

import TaskStatusBadge from '../components/TaskStatusBadge'
import TaskTimeline from '../components/TaskTimeline'
import { tasksApi } from '../_lib/tasksApi'
import { findPersona } from '../_lib/personas'
import { ACTIVE_STATUSES, taskTitleOf, relativeTime } from '../_lib/statusMap'
import type { AgentTask, TaskEvent } from '../../../types/agentTask'
import './index.scss'

const POLL_MS = 1_000

export default function TaskDetail() {
  const router = useRouter()
  const id = (router.params?.id as string) || ''

  const [task, setTask] = useState<AgentTask | null>(null)
  const [events, setEvents] = useState<TaskEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showReject, setShowReject] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [acting, setActing] = useState(false)

  const lastEventTsRef = useRef<string>('')
  const pollRef = useRef<NodeJS.Timeout | null>(null)
  const visibleRef = useRef(true)

  const refreshTask = useCallback(async () => {
    if (!id) return
    try {
      const t = await tasksApi.getTask(id)
      setTask(t)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    }
  }, [id])

  const refreshEvents = useCallback(async () => {
    if (!id) return
    try {
      const evs = await tasksApi.getEvents(id, lastEventTsRef.current || undefined)
      if (!evs || evs.length === 0) return
      setEvents((prev) => mergeEvents(prev, evs))
      lastEventTsRef.current = evs.reduce(
        (acc, ev) => (ev.timestamp > acc ? ev.timestamp : acc),
        lastEventTsRef.current,
      )
    } catch {
      // 静默失败，下个 tick 再试
    }
  }, [id])

  // 初次加载
  useEffect(() => {
    let cancelled = false
    if (!id) {
      setLoading(false)
      setError('缺少任务 ID')
      return
    }
    Promise.all([tasksApi.getTask(id), tasksApi.getEvents(id)])
      .then(([t, evs]) => {
        if (cancelled) return
        setTask(t)
        setEvents(evs)
        lastEventTsRef.current = evs.reduce(
          (acc, ev) => (ev.timestamp > acc ? ev.timestamp : acc),
          '',
        )
      })
      .catch((e) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : '加载失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  // polling：1s 拉 events，5 次拉一次任务（5s）以减少 task 主体 IO
  useEffect(() => {
    if (!id) return
    let tick = 0
    const start = () => {
      stop()
      pollRef.current = setInterval(() => {
        if (!visibleRef.current) return
        tick++
        void refreshEvents()
        if (tick % 5 === 0) void refreshTask()
      }, POLL_MS)
    }
    const stop = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
    start()
    return stop
  }, [id, refreshEvents, refreshTask])

  useDidShow(() => {
    visibleRef.current = true
    void refreshTask()
    void refreshEvents()
  })
  useDidHide(() => {
    visibleRef.current = false
  })

  const persona = task ? findPersona(task.agent_persona) : null

  const isActive = useMemo(() => task && ACTIVE_STATUSES.includes(task.status), [task])
  const needsApproval = task?.status === 'needs_approval'
  const isFinal = task && ['done', 'failed', 'cancelled'].includes(task.status)

  const handleCancel = async () => {
    if (!task || acting) return
    const ok = await new Promise<boolean>((resolve) => {
      Taro.showModal({
        title: '取消任务',
        content: `确定要取消「${taskTitleOf(task.payload, task.id)}」吗？`,
        confirmText: '确定取消',
        cancelText: '保留',
        success: (r) => resolve(Boolean(r.confirm)),
        fail: () => resolve(false),
      })
    })
    if (!ok) return
    setActing(true)
    try {
      const t = await tasksApi.cancelTask(task.id)
      setTask(t)
      Taro.showToast({ title: '已取消', icon: 'success' })
    } catch (e) {
      Taro.showToast({ title: e instanceof Error ? e.message : '取消失败', icon: 'none' })
    } finally {
      setActing(false)
      void refreshEvents()
    }
  }

  const handleApprove = async () => {
    if (!task || acting) return
    setActing(true)
    try {
      const t = await tasksApi.approveTask(task.id)
      setTask(t)
      Taro.showToast({ title: '已批准', icon: 'success' })
    } catch (e) {
      Taro.showToast({ title: e instanceof Error ? e.message : '操作失败', icon: 'none' })
    } finally {
      setActing(false)
      void refreshEvents()
    }
  }

  const handleReject = async () => {
    if (!task || acting) return
    if (!rejectReason.trim()) {
      Taro.showToast({ title: '请填写驳回理由', icon: 'none' })
      return
    }
    setActing(true)
    try {
      const t = await tasksApi.rejectTask(task.id, { reason: rejectReason.trim() })
      setTask(t)
      setShowReject(false)
      setRejectReason('')
      Taro.showToast({ title: '已驳回', icon: 'success' })
    } catch (e) {
      Taro.showToast({ title: e instanceof Error ? e.message : '操作失败', icon: 'none' })
    } finally {
      setActing(false)
      void refreshEvents()
    }
  }

  const handleRedo = async () => {
    if (!task || acting) return
    setActing(true)
    try {
      const fresh = await tasksApi.createTask({
        agent_persona: task.agent_persona,
        priority: task.priority,
        payload: task.payload,
      })
      Taro.showToast({ title: '已创建新任务', icon: 'success' })
      Taro.redirectTo({ url: `/subpackages/tasks/detail/index?id=${encodeURIComponent(fresh.id)}` })
    } catch (e) {
      Taro.showToast({ title: e instanceof Error ? e.message : '创建失败', icon: 'none' })
    } finally {
      setActing(false)
    }
  }

  if (loading && !task) {
    return (
      <View className='td-state'>
        <Text className='td-state__text'>正在加载…</Text>
      </View>
    )
  }
  if (!task) {
    return (
      <View className='td-state'>
        <Text className='td-state__text'>{error ?? '未找到任务'}</Text>
      </View>
    )
  }

  const title = taskTitleOf(task.payload, task.id)
  const userInput = task.payload?.user_input as string | undefined
  const approvalSummary = task.payload?.approval_summary as string | undefined
  const result = task.result
  const summary = result && typeof result.summary === 'string' ? result.summary : null

  return (
    <View className='td'>
      <ScrollView className='td__scroll' scrollY enableBackToTop>
        {/* header */}
        <View className='td-card'>
          <View className='td-card__head'>
            <Text className='td-card__emoji'>{persona?.emoji ?? '🤖'}</Text>
            <View className='td-card__head-text'>
              <Text className='td-card__persona'>{persona?.name ?? task.agent_persona}</Text>
              <Text className='td-card__time'>
                创建于 {relativeTime(task.created_at)} · 更新 {relativeTime(task.updated_at)}
              </Text>
            </View>
            <TaskStatusBadge status={task.status} size='md' />
          </View>
          <Text className='td-card__title'>{title}</Text>
          {userInput && task.payload?.title ? (
            <Text className='td-card__user-input'>{userInput}</Text>
          ) : null}
          {needsApproval && approvalSummary ? (
            <View className='td-card__approval'>
              <Text className='td-card__approval-tag'>需要你的审批</Text>
              <Text className='td-card__approval-text'>{approvalSummary}</Text>
            </View>
          ) : null}
        </View>

        {/* error */}
        {task.error ? (
          <View className='td-result td-result--error'>
            <Text className='td-result__title'>错误</Text>
            <Text className='td-result__text'>{task.error.message}</Text>
            {task.error.code ? <Text className='td-result__sub'>code: {task.error.code}</Text> : null}
          </View>
        ) : null}

        {/* result */}
        {summary ? (
          <View className='td-result td-result--done'>
            <Text className='td-result__title'>执行结果</Text>
            <Text className='td-result__text'>{summary}</Text>
          </View>
        ) : null}

        {/* timeline */}
        <View className='td-section'>
          <Text className='td-section__title'>事件流</Text>
          <Text className='td-section__sub'>1 秒自动刷新 · 共 {events.length} 条</Text>
          <TaskTimeline events={events} />
        </View>
      </ScrollView>

      {/* 操作栏 */}
      <View className='td-actions'>
        {needsApproval ? (
          <>
            <View
              className='td-actions__btn td-actions__btn--ghost'
              onClick={() => setShowReject(true)}
              hoverClass='td-actions__btn--hover'
            >
              <Text className='td-actions__btn-text td-actions__btn-text--ghost'>驳回</Text>
            </View>
            <View
              className='td-actions__btn td-actions__btn--primary'
              onClick={handleApprove}
              hoverClass='td-actions__btn--hover'
            >
              <Text className='td-actions__btn-text td-actions__btn-text--primary'>批准</Text>
            </View>
          </>
        ) : isActive ? (
          <View
            className='td-actions__btn td-actions__btn--danger'
            onClick={handleCancel}
            hoverClass='td-actions__btn--hover'
          >
            <Text className='td-actions__btn-text td-actions__btn-text--danger'>取消任务</Text>
          </View>
        ) : isFinal ? (
          <View
            className='td-actions__btn td-actions__btn--primary'
            onClick={handleRedo}
            hoverClass='td-actions__btn--hover'
          >
            <Text className='td-actions__btn-text td-actions__btn-text--primary'>再跑一次</Text>
          </View>
        ) : null}
      </View>

      {/* 驳回理由 mask */}
      {showReject ? (
        <View className='td-mask' onClick={() => setShowReject(false)}>
          <View className='td-mask__sheet' catchMove onClick={(e) => e.stopPropagation()}>
            <Text className='td-mask__title'>驳回任务</Text>
            <Text className='td-mask__desc'>请填写理由，将记录到任务时间线</Text>
            <Input
              className='td-mask__input'
              value={rejectReason}
              onInput={(e) => setRejectReason(e.detail.value)}
              placeholder='例如：金额与发票不符，请重新核对'
              maxlength={120}
            />
            <View className='td-mask__btns'>
              <View
                className='td-mask__btn td-mask__btn--ghost'
                onClick={() => {
                  setShowReject(false)
                  setRejectReason('')
                }}
              >
                <Text className='td-mask__btn-text'>取消</Text>
              </View>
              <View
                className='td-mask__btn td-mask__btn--danger'
                onClick={handleReject}
              >
                <Text className='td-mask__btn-text td-mask__btn-text--invert'>确定驳回</Text>
              </View>
            </View>
          </View>
        </View>
      ) : null}
    </View>
  )
}

function mergeEvents(prev: TaskEvent[], add: TaskEvent[]): TaskEvent[] {
  if (add.length === 0) return prev
  const seen = new Set<string>()
  const out: TaskEvent[] = []
  for (const ev of [...prev, ...add]) {
    const key = `${ev.timestamp}-${ev.event_type}-${stableHash(ev.payload)}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push(ev)
  }
  return out
}

function stableHash(p: unknown): string {
  try {
    return JSON.stringify(p)
  } catch {
    return String(p)
  }
}

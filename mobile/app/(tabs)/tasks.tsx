// -*- coding: utf-8 -*-
/**
 * 任务 tab 占位页（V3 P17-A 输出，待 P17-C 替换）。
 *
 * 注意：本文件覆盖了 V2 时期的 `app/tasks.tsx`（已通过 (tabs) router segment 优先生效）。
 * V2 老路由 `/tasks` 仍可由 `app/tasks.tsx` 直接服务，互不冲突。
 *
 * P17-C 接入计划：
 *   - agentTasksApi.listTasks({ limit: 50 }) 拉列表
 *   - 按 status 分组：进行中 / 待审批 / 已完成 / 失败
 *   - 进入详情用 router.push(`/(tabs)/tasks/${id}`)
 *   - 用 pollTaskUntilDone 实时刷新进行中任务
 */

import React from 'react'
import { PlaceholderScreen } from '@/components/Layout'

export default function TasksTabScreen() {
  return (
    <PlaceholderScreen
      title="任务加载中..."
      hint={'P17-C 完成后将显示 agent 任务中心\n（进行中 / 待审批 / 已完成 / 失败）'}
    />
  )
}

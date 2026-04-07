import type { ApprovalItem, TaskItem } from '@/types/api'

export type TaskAction = {
  label: string
  nextStatus: TaskItem['status']
  tone: 'primary' | 'secondary'
}

export type ApprovalAction = {
  label: string
  action: 'approve' | 'reject' | 'withdraw'
  tone: 'primary' | 'danger' | 'secondary'
}

export function getTaskActions(status: TaskItem['status']): TaskAction[] {
  if (status === 'todo') {
    return [{ label: '开始处理', nextStatus: 'in_progress', tone: 'primary' }]
  }

  if (status === 'in_progress') {
    return [
      { label: '标记完成', nextStatus: 'done', tone: 'primary' },
      { label: '退回待办', nextStatus: 'todo', tone: 'secondary' },
    ]
  }

  return [{ label: '重新打开', nextStatus: 'todo', tone: 'secondary' }]
}

export function getApprovalActions(status: ApprovalItem['status']): ApprovalAction[] {
  if (status !== 'pending') {
    return []
  }

  return [
    { label: '通过', action: 'approve', tone: 'primary' },
    { label: '驳回', action: 'reject', tone: 'danger' },
    { label: '撤回', action: 'withdraw', tone: 'secondary' },
  ]
}

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

export function getDetailLoadErrorMessage(error: unknown, fallback: string): string {
  const candidate = typeof error === 'object' && error !== null
    ? error as { status?: number; statusCode?: number; message?: string }
    : null
  const status = candidate?.status ?? candidate?.statusCode
  const message = typeof error === 'string' ? error : candidate?.message || ''

  if (status === 401 || /401|登录|过期/.test(message)) {
    return '登录已过期，请重新登录'
  }
  if (status === 403 || /403|权限|Forbidden/i.test(message)) {
    return '无权限查看该内容'
  }
  if (status === 404 || /404|不存在|Not Found/i.test(message)) {
    return '内容不存在或已被删除'
  }
  if (/network|timeout|abort|failed to fetch|网络|超时/i.test(message)) {
    return '网络连接失败，请检查后重试'
  }
  return message || fallback
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

import { describe, expect, it } from 'vitest'
import { getApprovalActions, getDetailLoadErrorMessage, getTaskActions } from './detail-model'

describe('getTaskActions', () => {
  it('returns allowed transitions for todo, in progress and done tasks', () => {
    expect(getTaskActions('todo')).toEqual([
      expect.objectContaining({ label: '开始处理', nextStatus: 'in_progress' }),
    ])

    expect(getTaskActions('in_progress')).toEqual([
      expect.objectContaining({ label: '标记完成', nextStatus: 'done' }),
      expect.objectContaining({ label: '退回待办', nextStatus: 'todo' }),
    ])

    expect(getTaskActions('done')).toEqual([
      expect.objectContaining({ label: '重新打开', nextStatus: 'todo' }),
    ])
  })
})

describe('getApprovalActions', () => {
  it('returns review actions only for pending approvals', () => {
    expect(getApprovalActions('pending')).toEqual([
      expect.objectContaining({ label: '通过', action: 'approve' }),
      expect.objectContaining({ label: '驳回', action: 'reject' }),
      expect.objectContaining({ label: '撤回', action: 'withdraw' }),
    ])

    expect(getApprovalActions('approved')).toEqual([])
    expect(getApprovalActions('rejected')).toEqual([])
  })
})

describe('getDetailLoadErrorMessage', () => {
  it('maps auth, permission, missing and network failures to explicit user messages', () => {
    expect(getDetailLoadErrorMessage({ status: 401 }, '加载失败')).toBe('登录已过期，请重新登录')
    expect(getDetailLoadErrorMessage({ statusCode: 403 }, '加载失败')).toBe('无权限查看该内容')
    expect(getDetailLoadErrorMessage({ message: '404 Not Found' }, '加载失败')).toBe('内容不存在或已被删除')
    expect(getDetailLoadErrorMessage({ message: 'Network request failed' }, '加载失败')).toBe('网络连接失败，请检查后重试')
    expect(getDetailLoadErrorMessage({}, '加载失败')).toBe('加载失败')
  })

  it('maps string transport errors instead of hiding them behind fallback copy', () => {
    expect(getDetailLoadErrorMessage('timeout while loading task detail', '任务加载失败')).toBe('网络连接失败，请检查后重试')
    expect(getDetailLoadErrorMessage('Failed to fetch', '消息加载失败')).toBe('网络连接失败，请检查后重试')
  })

  it('prefers status-specific messages over misleading backend text', () => {
    expect(getDetailLoadErrorMessage({ status: 403, message: '404 Not Found' }, '加载失败')).toBe('无权限查看该内容')
    expect(getDetailLoadErrorMessage({ status: 401, message: 'Forbidden' }, '加载失败')).toBe('登录已过期，请重新登录')
  })
})

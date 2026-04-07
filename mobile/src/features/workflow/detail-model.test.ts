import { describe, expect, it } from 'vitest'
import { getApprovalActions, getTaskActions } from './detail-model'

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

import { describe, expect, it } from 'vitest'
import { buildInboxOverviewCards, inboxQuickActions } from './model'

describe('buildInboxOverviewCards', () => {
  it('builds four inbox overview cards in stable order', () => {
    const cards = buildInboxOverviewCards({
      tasks: 4,
      approvals: 2,
      messages: 7,
      notifications: 3,
    })

    expect(cards.map((item) => item.key)).toEqual([
      'tasks',
      'approvals',
      'messages',
      'notifications',
    ])
    expect(cards[0]).toMatchObject({
      label: '待办任务',
      value: 4,
      route: '/tasks',
    })
    expect(cards[1]).toMatchObject({
      label: '待审批',
      value: 2,
      route: '/approvals',
    })
  })
})

describe('inboxQuickActions', () => {
  it('exposes inbox-first quick actions for mobile workbench', () => {
    expect(inboxQuickActions).toEqual([
      expect.objectContaining({ key: 'tasks', route: '/tasks', label: '任务中心' }),
      expect.objectContaining({ key: 'approvals', route: '/approvals', label: '审批处理' }),
      expect.objectContaining({ key: 'chat', route: '/messages', label: '消息跟进' }),
      expect.objectContaining({ key: 'contracts', route: '/contracts', label: '合同查看' }),
    ])
  })
})

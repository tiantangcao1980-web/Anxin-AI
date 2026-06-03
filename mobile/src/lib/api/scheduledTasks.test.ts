// -*- coding: utf-8 -*-
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  client: {
    get: vi.fn(),
    put: vi.fn(),
  },
}))

vi.mock('./client', () => ({
  getApiClient: () => mocks.client,
}))

import { listScheduledTasks, toggleScheduledTask } from './scheduledTasks'

const sample = {
  id: 'st-001',
  name: '采购合同 30 天到期提醒',
  kind: 'contract_expiry_alert',
  cron: '0 9 * * *',
  cron_human: '每天 09:00',
  status: 'active',
  last_run_at: '2026-04-29T01:00:00Z',
  next_run_at: '2026-04-30T01:00:00Z',
  last_run_ok: true,
  agent_persona: 'legal',
}

describe('scheduledTasks api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('list 调 GET /scheduled-tasks 并返回 data', async () => {
    mocks.client.get.mockResolvedValue({ data: [sample] })
    const res = await listScheduledTasks()
    expect(mocks.client.get).toHaveBeenCalledWith('/scheduled-tasks')
    expect(res).toEqual([sample])
  })

  it('list data 为空时返回空数组', async () => {
    mocks.client.get.mockResolvedValue({ data: undefined })
    const res = await listScheduledTasks()
    expect(res).toEqual([])
  })

  it('toggle 调 PUT /scheduled-tasks/{id}/toggle body {status}', async () => {
    mocks.client.put.mockResolvedValue({ data: { ...sample, status: 'paused' } })
    const res = await toggleScheduledTask('st-001', 'paused')
    expect(mocks.client.put).toHaveBeenCalledWith(
      '/scheduled-tasks/st-001/toggle',
      { status: 'paused' },
    )
    expect(res.status).toBe('paused')
  })

  it('toggle 对 id 做 URL 编码', async () => {
    mocks.client.put.mockResolvedValue({ data: sample })
    await toggleScheduledTask('a/b', 'active')
    expect(mocks.client.put).toHaveBeenCalledWith(
      '/scheduled-tasks/a%2Fb/toggle',
      { status: 'active' },
    )
  })

  it('错误向上抛出（页面负责处理）', async () => {
    mocks.client.get.mockRejectedValue(new Error('boom'))
    await expect(listScheduledTasks()).rejects.toThrow('boom')
  })
})

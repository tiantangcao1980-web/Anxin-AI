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

import { listPlugins, togglePlugin } from './plugins'

const sample = {
  id: 'pl-001',
  name: 'contract_review',
  display_name: '合同审查',
  source: 'official',
  status: 'enabled',
  description: '自动审查合同关键条款',
  publisher: '安心官方',
}

describe('plugins api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('list 调 GET /plugins 并返回 data', async () => {
    mocks.client.get.mockResolvedValue({ data: [sample] })
    const res = await listPlugins()
    expect(mocks.client.get).toHaveBeenCalledWith('/plugins')
    expect(res).toEqual([sample])
  })

  it('list data 为空时返回空数组', async () => {
    mocks.client.get.mockResolvedValue({ data: undefined })
    const res = await listPlugins()
    expect(res).toEqual([])
  })

  it('toggle 调 PUT /plugins/{id}/toggle body {enabled}', async () => {
    mocks.client.put.mockResolvedValue({ data: { ...sample, status: 'disabled' } })
    const res = await togglePlugin('pl-001', false)
    expect(mocks.client.put).toHaveBeenCalledWith(
      '/plugins/pl-001/toggle',
      { enabled: false },
    )
    expect(res.status).toBe('disabled')
  })

  it('toggle 对 id 做 URL 编码（含 mcp: 前缀）', async () => {
    mocks.client.put.mockResolvedValue({ data: sample })
    await togglePlugin('mcp:server-a', true)
    expect(mocks.client.put).toHaveBeenCalledWith(
      '/plugins/mcp%3Aserver-a/toggle',
      { enabled: true },
    )
  })

  it('错误向上抛出（页面负责处理）', async () => {
    mocks.client.get.mockRejectedValue(new Error('boom'))
    await expect(listPlugins()).rejects.toThrow('boom')
  })
})

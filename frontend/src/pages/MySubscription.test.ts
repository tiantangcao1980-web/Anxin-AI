import { describe, expect, it } from 'vitest'
import {
  normalizeOrderData,
  normalizeRefundData,
  normalizeSubscriptionData,
} from './MySubscription'

describe('MySubscription data normalization', () => {
  it('keeps needer and provider subscriptions as separate client records', () => {
    const subscriptions = normalizeSubscriptionData([
      {
        id: 'sub-needer',
        client_type: 'needer',
        status: 'active',
        current_period_end: '2026-06-06',
        auto_renew: true,
        plan: { id: 'plan-needer', name: '需求方 Pro', ai_quota: 200, storage_gb: 20 },
      },
      {
        id: 'sub-provider',
        client_type: 'provider',
        status: 'trial',
        trial_ends_at: '2026-05-20T00:00:00Z',
        auto_renew: false,
        plan: { id: 'plan-provider', name: '服务方 Pro', ai_quota: 500, storage_gb: 50 },
      },
    ])

    expect(subscriptions).toEqual([
      expect.objectContaining({
        id: 'sub-needer',
        clientType: 'needer',
        planName: '需求方 Pro',
        planId: 'plan-needer',
        status: 'active',
        expiresAt: '2026-06-06',
        autoRenew: true,
        aiTotal: 200,
        storageTotalGB: 20,
      }),
      expect.objectContaining({
        id: 'sub-provider',
        clientType: 'provider',
        planName: '服务方 Pro',
        planId: 'plan-provider',
        status: 'trial',
        expiresAt: '2026-05-20T00:00:00Z',
        autoRenew: false,
        aiTotal: 500,
        storageTotalGB: 50,
      }),
    ])
  })

  it('defaults unknown client types to needer without dropping provider subscriptions', () => {
    const subscriptions = normalizeSubscriptionData({
      subscriptions: [
        { id: 'legacy-sub', client_type: null, plan_name: '历史套餐' },
        { id: 'provider-sub', clientType: 'provider', planName: '律师套餐' },
      ],
    })

    expect(subscriptions.map(sub => sub.clientType)).toEqual(['needer', 'provider'])
  })

  it('normalizes orders and refunds from backend response variants', () => {
    expect(normalizeOrderData({
      orders: [{ id: 'order-1', created_at: '2026-05-06', amount: '99', status: 'paid' }],
      subscriptions: [{ orders: [{ id: 'order-2', createdAt: '2026-05-07', amount: 199 }] }],
    })).toEqual([
      expect.objectContaining({ id: 'order-1', date: '2026-05-06', amount: 99, status: 'paid' }),
      expect.objectContaining({ id: 'order-2', date: '2026-05-07', amount: 199, status: 'pending' }),
    ])

    expect(normalizeRefundData({
      refunds: [{ id: 'refund-1', order_id: 'order-1', amount: 99, status: 'processed' }],
    })).toEqual([
      expect.objectContaining({
        id: 'refund-1',
        orderId: 'order-1',
        amount: 99,
        status: 'processed',
      }),
    ])
  })
})

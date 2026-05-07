import { describe, expect, it } from 'vitest'
import { filterPlansForClient, normalizePricingPlans } from './Pricing'

describe('Pricing plan normalization', () => {
  it('normalizes client types and price fields from backend plans', () => {
    const plans = normalizePricingPlans([
      {
        id: 'plan-needer',
        name: '需求方 Pro',
        client_type: 'needer',
        base_price: 99,
        features: { im_messaging: true, due_diligence: false },
      },
      {
        id: 'plan-provider',
        name: '服务方 Pro',
        client_type: 'provider',
        monthlyPrice: 199,
        features: ['案件管理', '获客工具'],
      },
      {
        id: 'plan-both',
        name: '通用企业版',
        client_type: 'both',
        monthly_price: 399,
      },
    ])

    expect(plans).toEqual([
      expect.objectContaining({
        id: 'plan-needer',
        clientType: 'needer',
        monthlyPrice: 99,
        features: ['im_messaging'],
      }),
      expect.objectContaining({
        id: 'plan-provider',
        clientType: 'provider',
        monthlyPrice: 199,
        features: ['案件管理', '获客工具'],
      }),
      expect.objectContaining({
        id: 'plan-both',
        clientType: 'both',
        monthlyPrice: 399,
      }),
    ])
  })

  it('filters tab plans without dropping plans marked for both clients', () => {
    const plans = normalizePricingPlans([
      { id: 'needer', name: '需求方', client_type: 'needer' },
      { id: 'provider', name: '服务方', client_type: 'provider' },
      { id: 'both', name: '通用', client_type: 'both' },
    ])

    expect(filterPlansForClient(plans, 'needer').map(plan => plan.id)).toEqual(['needer', 'both'])
    expect(filterPlansForClient(plans, 'provider').map(plan => plan.id)).toEqual(['provider', 'both'])
  })
})

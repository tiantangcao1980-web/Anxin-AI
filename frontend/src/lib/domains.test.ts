// V3 8 大业务域元数据完整性 smoke 测试
//
// 与 mobile/src/theme/colors.test.ts 和 mini-program/src/styles/design-tokens.test.ts 对称。
// 防止：
//   - DOMAINS 注册表被误删 / 顺序错乱 / 字段缺失
//   - 业务域 colorClass / surfaceClass 与 Tailwind utility 不一致
//   - 跨端业务域 ID 漂移

import { describe, expect, it } from 'vitest'
import {
  DOMAINS,
  DOMAIN_BY_ID,
  inferDomainFromPath,
  type DomainId,
} from './domains'

describe('frontend domains · V3 8 大业务域元数据', () => {
  it('DOMAINS 必须包含 8 个业务域，按固定顺序', () => {
    const expected: DomainId[] = [
      'legal',
      'finance',
      'tax',
      'compliance',
      'operations',
      'growth',
      'content',
      'global',
    ]
    expect(DOMAINS.map((d) => d.id)).toEqual(expected)
  })

  it('每个域都有 label / labelEn / tagline / defaultPath / icon / cssVar', () => {
    for (const d of DOMAINS) {
      expect(d.label.length).toBeGreaterThan(0)
      expect(d.labelEn.length).toBeGreaterThan(0)
      expect(d.tagline.length).toBeGreaterThan(0)
      expect(d.defaultPath.startsWith('/')).toBe(true)
      expect(typeof d.icon).toBe('object') // lucide-react 是 ForwardRefExoticComponent
      expect(d.cssVar).toMatch(/^domain-(legal|finance|tax|compliance|operations|growth|content|global)$/)
    }
  })

  it('colorClass / surfaceClass 与 Tailwind utility 命名一致', () => {
    for (const d of DOMAINS) {
      expect(d.colorClass).toBe(`text-domain-${d.id}`)
      expect(d.surfaceClass).toBe(`bg-domain-${d.id}-surface`)
    }
  })

  it('每个业务域的 cssVar 都精确匹配 id', () => {
    for (const d of DOMAINS) {
      expect(d.cssVar).toBe(`domain-${d.id}`)
    }
  })

  it('DOMAIN_BY_ID 与 DOMAINS 双向一致', () => {
    expect(Object.keys(DOMAIN_BY_ID).sort()).toEqual(DOMAINS.map((d) => d.id).sort())
    for (const d of DOMAINS) {
      expect(DOMAIN_BY_ID[d.id]).toBe(d)
    }
  })

  it('中文 label 必须与跨端约定一致（与 mobile / mini-program 对齐）', () => {
    const expectedLabels: Record<DomainId, string> = {
      legal: '法务',
      finance: '财务',
      tax: '税务',
      compliance: '合规',
      operations: '经营管理',
      growth: '调研获客',
      content: '内容产出',
      global: '出海跨境',
    }
    for (const d of DOMAINS) {
      expect(d.label).toBe(expectedLabels[d.id])
    }
  })

  it('inferDomainFromPath: 直接前缀匹配', () => {
    expect(inferDomainFromPath('/case-center/123')?.id).toBe('legal')
    expect(inferDomainFromPath('/investigation/x')?.id).toBe('growth')
    expect(inferDomainFromPath('/dashboard')?.id).toBe('operations')
  })

  it('inferDomainFromPath: V2→V3 路径兜底（/contract-* / /find-lawyer / /knowledge / /monitoring）', () => {
    expect(inferDomainFromPath('/contract-review')?.id).toBe('legal')
    expect(inferDomainFromPath('/find-lawyer')?.id).toBe('legal')
    expect(inferDomainFromPath('/knowledge-base')?.id).toBe('legal')
    expect(inferDomainFromPath('/monitoring')?.id).toBe('growth')
  })

  it('inferDomainFromPath: 未知路径返回 null', () => {
    expect(inferDomainFromPath('/totally-unknown-path-xyz')).toBeNull()
  })
})

// V3 8 大业务域元数据守护 (Reset 后)
//
// 2026-05 Reset：旧版守护 8 域 color/surface/cssVar 不漂移。
// 新版反向：守护 DomainMeta 不要重新引入 color/cssVar/colorClass/surfaceClass 字段。
//
// 与 mobile/src/theme/colors.test.ts、mini-program/src/styles/design-tokens.test.ts 对称。

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  DOMAINS,
  DOMAIN_BY_ID,
  inferDomainFromPath,
  type DomainId,
} from './domains'

describe('frontend domains · V3 8 大业务域元数据 (Reset)', () => {
  it('DOMAINS 必须包含 8 个业务域，按固定顺序', () => {
    const expected: DomainId[] = [
      'legal', 'finance', 'tax', 'compliance',
      'operations', 'growth', 'content', 'global',
    ]
    expect(DOMAINS.map((d) => d.id)).toEqual(expected)
  })

  it('每个域必备字段：id / label / labelEn / tagline / defaultPath / icon', () => {
    for (const d of DOMAINS) {
      expect(d.id).toBeTruthy()
      expect(d.label.length).toBeGreaterThan(0)
      expect(d.labelEn.length).toBeGreaterThan(0)
      expect(d.tagline.length).toBeGreaterThan(0)
      expect(d.defaultPath.startsWith('/')).toBe(true)
      expect(typeof d.icon).toBe('object') // lucide ForwardRefExoticComponent
    }
  })

  it('【反向断言】DomainMeta 禁止重新引入 color/surface/cssVar/colorClass/surfaceClass 字段', () => {
    for (const d of DOMAINS) {
      const dAny = d as unknown as Record<string, unknown>
      expect(dAny.color).toBeUndefined()
      expect(dAny.surface).toBeUndefined()
      expect(dAny.cssVar).toBeUndefined()
      expect(dAny.colorClass).toBeUndefined()
      expect(dAny.surfaceClass).toBeUndefined()
    }
  })

  it('【反向断言】domains.ts 源码不得出现 hsl(...) / #色码 / colorClass / cssVar 字面值', () => {
    const file = path.resolve(__dirname, 'domains.ts')
    const text = fs.readFileSync(file, 'utf-8')
    expect(text).not.toMatch(/colorClass\s*:/)
    expect(text).not.toMatch(/surfaceClass\s*:/)
    expect(text).not.toMatch(/cssVar\s*:/)
    expect(text).not.toMatch(/#[0-9A-Fa-f]{6}/) // hex 色码
    expect(text).not.toMatch(/hsl\s*\(\s*\d/)   // 内联 hsl 色
  })

  it('DOMAIN_BY_ID 与 DOMAINS 双向一致', () => {
    expect(Object.keys(DOMAIN_BY_ID).sort()).toEqual(DOMAINS.map((d) => d.id).sort())
  })

  it('中文 label 必须与跨端约定一致', () => {
    const expectedLabels: Record<DomainId, string> = {
      legal: '法务', finance: '财务', tax: '税务', compliance: '合规',
      operations: '经营管理', growth: '调研获客', content: '内容产出', global: '出海跨境',
    }
    for (const d of DOMAINS) {
      expect(d.label).toBe(expectedLabels[d.id])
    }
  })

  it('inferDomainFromPath: 9 条 Layout 路径全部覆盖', () => {
    expect(inferDomainFromPath('/case-center')?.id).toBe('legal')
    expect(inferDomainFromPath('/management')?.id).toBe('legal')
    expect(inferDomainFromPath('/agent-approvals')?.id).toBe('compliance')
    expect(inferDomainFromPath('/find-lawyer')?.id).toBe('legal')
    expect(inferDomainFromPath('/documents')?.id).toBe('content')
    expect(inferDomainFromPath('/investigation')?.id).toBe('growth')
    expect(inferDomainFromPath('/monitoring')?.id).toBe('growth')
    expect(inferDomainFromPath('/knowledge-base')?.id).toBe('legal')
    expect(inferDomainFromPath('/dashboard')?.id).toBe('operations')
  })

  it('未知路径返回 null', () => {
    expect(inferDomainFromPath('/totally-unknown-xyz')).toBeNull()
  })
})

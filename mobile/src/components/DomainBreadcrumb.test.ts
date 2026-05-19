// -*- coding: utf-8 -*-
// Mobile DomainBreadcrumb 守护测试 (Reset 后)
//
// 2026-05 Reset：组件改为纯文字 micro UPPERCASE 版（无 Ionicons / 无域色）。
// 守护点改为：metadata 可用 + Reset 反向断言（无 color/surface/Ionicons 字面值）。

import { describe, expect, it } from 'vitest'
import { domainMeta, type DomainId } from '../theme/colors'

describe('mobile · DomainBreadcrumb 守护 (Reset)', () => {
  it('所有 8 个 DomainId 都有 domainMeta 可用', () => {
    const ids: DomainId[] = [
      'legal', 'finance', 'tax', 'compliance',
      'operations', 'growth', 'content', 'global',
    ]
    for (const id of ids) {
      expect(domainMeta[id]).toBeDefined()
      expect(domainMeta[id].labelZh).toBeTruthy()
      expect(domainMeta[id].labelEn).toBeTruthy()
    }
  })

  it('【Reset】domainMeta 不再含 color / surface 字段', () => {
    const ids: DomainId[] = ['legal', 'finance', 'tax', 'compliance', 'operations', 'growth', 'content', 'global']
    for (const id of ids) {
      const metaAny = domainMeta[id] as unknown as Record<string, unknown>
      expect(metaAny.color).toBeUndefined()
      expect(metaAny.surface).toBeUndefined()
    }
  })

  it('DomainBreadcrumb.tsx 导出 compact / moduleName 两种用法', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'DomainBreadcrumb.tsx'),
      'utf-8',
    )
    expect(text).toContain('compact')
    expect(text).toContain('moduleName')
    expect(text).toMatch(/export\s+function\s+DomainBreadcrumb/)
  })

  it('【Reset】DomainBreadcrumb.tsx 不再 import Ionicons / 不再用 meta.color/surface', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'DomainBreadcrumb.tsx'),
      'utf-8',
    )
    // 仅扫 import / JSX 实际 code 中的 token 引用；注释里描述旧版的历史段落不受检查
    expect(text).not.toMatch(/import[^;]*@expo\/vector-icons/)
    expect(text).not.toMatch(/scale-outline|calculator-outline/) // 旧 Ionicons 映射
    expect(text).not.toMatch(/meta\.color\b/)    // 旧版用 meta.color
    expect(text).not.toMatch(/meta\.surface\b/)  // 旧版用 meta.surface
  })
})

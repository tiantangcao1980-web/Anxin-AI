// Mini-program DomainBreadcrumb 守护 (Reset 后)
//
// 2026-05 Reset：组件改为纯文字 micro UPPERCASE 版（无 emoji / 无域色）。
// 守护点：domainMeta 可用 + 反向断言（无 color/surface/emoji 字面值）。

import { describe, expect, it } from 'vitest'
import { domainMeta, type DomainId } from '@/styles/design-tokens'

describe('mini-program · DomainBreadcrumb 守护 (Reset)', () => {
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

  it('源码导出 compact / moduleName 两种用法', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'index.tsx'),
      'utf-8',
    )
    expect(text).toContain('compact')
    expect(text).toContain('moduleName')
    expect(text).toMatch(/export\s+default\s+function\s+DomainBreadcrumb/)
  })

  it('【Reset】源码不再有 DOMAIN_EMOJI 映射、不再有域色 inline style', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'index.tsx'),
      'utf-8',
    )
    expect(text).not.toMatch(/DOMAIN_EMOJI/)
    expect(text).not.toMatch(/meta\.color\b/)
    expect(text).not.toMatch(/meta\.surface\b/)
    expect(text).not.toMatch(/backgroundColor:\s*meta/)
  })

  it('SCSS 引用 design-tokens.scss', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'index.scss'),
      'utf-8',
    )
    expect(text).toContain('design-tokens.scss')
  })
})

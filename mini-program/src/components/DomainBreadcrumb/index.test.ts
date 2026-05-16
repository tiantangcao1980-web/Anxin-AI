// Mini Program DomainBreadcrumb 守护测试
// 不直接 import 组件源码（会拉入 @tarojs/components，node 环境解析坑），
// 改用字符串/数据层守护。

import { describe, expect, it } from 'vitest'
import { domain, type DomainId } from '@/styles/design-tokens'

describe('mini-program · DomainBreadcrumb 守护', () => {
  it('所有 8 个 DomainId 都有 domain 元数据可用', () => {
    const ids: DomainId[] = [
      'legal', 'finance', 'tax', 'compliance',
      'operations', 'growth', 'content', 'global',
    ]
    for (const id of ids) {
      expect(domain[id]).toBeDefined()
      expect(domain[id].color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(domain[id].surface).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(domain[id].labelZh).toBeTruthy()
    }
  })

  it('源码顶部明确与 frontend / mobile 视觉对齐', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'index.tsx'),
      'utf-8',
    )
    expect(text).toMatch(/frontend\s*\/\s*mobile DomainBreadcrumb/)
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

  it('DOMAIN_EMOJI 映射覆盖全 8 个 DomainId', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'index.tsx'),
      'utf-8',
    )
    const ids = ['legal', 'finance', 'tax', 'compliance', 'operations', 'growth', 'content', 'global']
    for (const id of ids) {
      // 形如 "legal: '⚖️'" 的字面值
      expect(text).toMatch(new RegExp(`${id}:\\s*'`))
    }
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

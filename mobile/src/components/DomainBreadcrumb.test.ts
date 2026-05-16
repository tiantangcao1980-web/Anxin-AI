// -*- coding: utf-8 -*-
// Mobile DomainBreadcrumb 守护测试
//
// 注意：本测试不直接 import DomainBreadcrumb.tsx 源码 — 它会间接拉入
// @expo/vector-icons，而该包在 node-only vitest 环境下有 ESM 解析坑。
// 改用：纯字符串/数据层守护（domain 元数据 + 源码文本断言）。
// runtime 渲染由 Expo Go / iOS Simulator smoke 覆盖。

import { describe, expect, it } from 'vitest'
import { domain, type DomainId } from '../theme/colors'

describe('mobile · DomainBreadcrumb 守护', () => {
  it('所有 8 个 DomainId 都有 mobile domain 元数据可用', () => {
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

  it('DomainBreadcrumb.tsx 源码顶部声明与 frontend 视觉对齐', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'DomainBreadcrumb.tsx'),
      'utf-8',
    )
    expect(text).toMatch(/frontend\/src\/components\/ui\/DomainBreadcrumb/)
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

  it('DomainBreadcrumb.tsx 覆盖 Ionicons 映射的全 8 个 DomainId', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const text = await fs.readFile(
      path.resolve(__dirname, 'DomainBreadcrumb.tsx'),
      'utf-8',
    )
    const ids = ['legal', 'finance', 'tax', 'compliance', 'operations', 'growth', 'content', 'global']
    for (const id of ids) {
      // 形如 "legal:      'scale-outline'," 的字面值，确保每个 id 都映射到了 Ionicons 名
      expect(text).toMatch(new RegExp(`${id}:\\s*'[a-z-]+'`))
    }
  })
})

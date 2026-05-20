// DomainBreadcrumb 守护测试 — 防止 inferDomainFromPath 与 Layout
// moduleSidebarConfig 的 9 个二级导航路径之间发生漂移

import { describe, expect, it } from 'vitest'
import { inferDomainFromPath } from '@/lib/domains'

describe('DomainBreadcrumb · inferDomainFromPath 覆盖 Layout 9 路径', () => {
  // 与 frontend/src/components/Layout.tsx moduleSidebarConfig 同步
  const cases: Array<[path: string, expectedDomain: string]> = [
    ['/case-center', 'legal'],
    ['/case-center/abc', 'legal'],
    ['/management', 'legal'],
    ['/agent-approvals', 'compliance'],
    ['/find-lawyer', 'legal'],
    ['/find-lawyer/123', 'legal'],
    ['/documents', 'content'],
    ['/investigation', 'growth'],
    ['/investigation/dd', 'growth'],
    ['/monitoring', 'growth'],
    ['/knowledge-base', 'legal'],
    ['/knowledge-graph', 'legal'],
    ['/firm/x', 'legal'],
    ['/lawyer-dashboard', 'legal'],
    ['/acquisition', 'growth'],
    ['/contract-review', 'legal'],
    ['/dashboard', 'operations'],
  ]

  for (const [path, expected] of cases) {
    it(`${path} → ${expected}`, () => {
      const meta = inferDomainFromPath(path)
      expect(meta?.id).toBe(expected)
    })
  }

  it('未知路径返回 null（不强行归类）', () => {
    expect(inferDomainFromPath('/completely-unknown-route-xyz')).toBeNull()
    expect(inferDomainFromPath('/')).toBeNull()
  })
})

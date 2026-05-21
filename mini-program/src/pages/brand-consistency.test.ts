// V3 品牌一致性守护 — 防止 V2「安心法务」时代术语在 mini-program 页面回归
//
// 跨页扫描页面文件，发现下列任一就 fail：
//   - 旧产品名："安心法务" / "安心智慧法务"
//   - V2 副标语："超级安心" / "让法律服务更简单"
//   - UniApp 残留："uni-mobile" / "uni-app" / "DCloud"
//
// V3 已扩展为 8 大业务域，pages/index 和 pages/me 应有相关定位文案。

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const PAGES_DIR = path.resolve(__dirname)

function readAllPageSources(): string {
  // 4 个主包页面 + 子包页面，全部拼成一个大字符串
  const buckets: string[] = []
  function walk(dir: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        walk(full)
        continue
      }
      if (!/\.(tsx?|scss)$/.test(entry.name)) continue
      if (entry.name.endsWith('.test.ts') || entry.name.endsWith('.test.tsx')) continue
      buckets.push(fs.readFileSync(full, 'utf-8'))
    }
  }
  walk(PAGES_DIR)
  return buckets.join('\n\n---FILE_SEPARATOR---\n\n')
}

describe('mini-program 页面 V3 品牌一致性', () => {
  const corpus = readAllPageSources()

  it('不出现 V2 旧品牌"安心法务" / "安心智慧法务"', () => {
    expect(corpus).not.toMatch(/安心法务/)
    expect(corpus).not.toMatch(/安心智慧法务/)
  })

  it('不出现 V2 副标"让法律服务更简单"', () => {
    expect(corpus).not.toContain('让法律服务更简单')
  })

  it('不残留 UniApp 路线相关字样', () => {
    expect(corpus).not.toMatch(/uni-mobile/i)
    expect(corpus).not.toMatch(/uni-app/i)
    expect(corpus).not.toMatch(/dcloud/i)
  })

  it('首页或个人中心至少有一处提到 V3 8 大业务定位', () => {
    // V3 定位关键词：制造业 / 8 大业务 / 全链路 任一即可，且应在 pages/index 或 pages/me
    const indexHomeText = fs.readFileSync(
      path.join(PAGES_DIR, 'index', 'index.tsx'),
      'utf-8',
    )
    const meText = fs.readFileSync(path.join(PAGES_DIR, 'me', 'index.tsx'), 'utf-8')
    const combined = indexHomeText + meText
    expect(combined).toMatch(/全链路|8 大业务|制造业/)
  })
})

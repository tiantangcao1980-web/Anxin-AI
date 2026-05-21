// V3 品牌一致性守护（子包扫描）—— 与 src/pages/brand-consistency.test.ts 对称。
//
// 主包 brand-consistency 只扫 src/pages/，本测试补齐 src/subpackages/
// （capabilities / personas / tasks 三个子包共 16+ 页面 + components）。

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const SUBPACKAGES_DIR = path.resolve(__dirname)

function readAllSubpackageSources(): string {
  const buckets: string[] = []
  function walk(dir: string) {
    if (!fs.existsSync(dir)) return
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        walk(path.join(dir, entry.name))
        continue
      }
      if (!/\.(tsx?|scss)$/.test(entry.name)) continue
      if (/\.(test|spec)\.tsx?$/.test(entry.name)) continue
      buckets.push(fs.readFileSync(path.join(dir, entry.name), 'utf-8'))
    }
  }
  walk(SUBPACKAGES_DIR)
  return buckets.join('\n\n---FILE_SEPARATOR---\n\n')
}

describe('mini-program subpackages · V3 品牌一致性', () => {
  const corpus = readAllSubpackageSources()

  it('subpackages 不再出现 V2 旧品牌"安心法务" / "安心智慧法务"', () => {
    expect(corpus).not.toMatch(/安心法务/)
    expect(corpus).not.toMatch(/安心智慧法务/)
  })

  it('subpackages 不出现 V2 副标"让法律服务更简单" / "超级安心智能助手系统"', () => {
    expect(corpus).not.toContain('让法律服务更简单')
    expect(corpus).not.toContain('超级安心智能助手系统')
  })

  it('subpackages 不残留 UniApp 路线字样（uni-mobile / uni-app / DCloud）', () => {
    expect(corpus).not.toMatch(/uni-mobile/i)
    expect(corpus).not.toMatch(/uni-app/i)
    expect(corpus).not.toMatch(/dcloud/i)
  })

  it('SCSS 文件应已 @import design-tokens.scss（除纯结构样式外）', () => {
    // 收集 subpackages 所有 .scss 文件
    const sources: { path: string; text: string }[] = []
    function walk(dir: string) {
      if (!fs.existsSync(dir)) return
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.isDirectory()) {
          walk(path.join(dir, entry.name))
          continue
        }
        if (!entry.name.endsWith('.scss')) continue
        const full = path.join(dir, entry.name)
        sources.push({ path: full, text: fs.readFileSync(full, 'utf-8') })
      }
    }
    walk(SUBPACKAGES_DIR)

    const missing: string[] = []
    for (const s of sources) {
      // 含 hex 颜色字面值的 .scss 必须 @import design-tokens
      const hasHex = /#[0-9A-Fa-f]{3,6}\b/.test(s.text)
      const hasImport = /design-tokens\.scss/.test(s.text)
      if (hasHex && !hasImport) {
        missing.push(path.relative(SUBPACKAGES_DIR, s.path))
      }
    }
    expect(missing).toEqual([])
  })

  it('subpackages 总 hex 字面量数 ≤ 200（监控渐进式迁移进度，2026-05-16 实测 141）', () => {
    const text = corpus
    const total = (text.match(/#[0-9A-Fa-f]{3,6}\b/g) || []).length
    // 当前实测 ~141，留 60 的余量；如果未来需要回退（如扩展新 token），改这条阈值
    expect(total).toBeLessThanOrEqual(200)
  })
})

// V3 品牌一致性守护（与 mobile/src/brand-consistency.test.ts 和
// mini-program/src/pages/brand-consistency.test.ts 对称）
//
// 扫描 frontend/src 关键页面源码，发现下列任一即 fail：
//   - V2 旧产品名："安心法务" / "安心智慧法务"
//   - V2 副标："让法律服务更简单" / "超级安心智能助手系统"
//   - UniApp 残留："uni-mobile" / "@dcloudio"
//
// 同时要求 Login 页和 Layout 必须保留 V3 关键文案（防止被回退）。

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC_DIR = path.resolve(__dirname)

function readCorpus(): string {
  const buckets: string[] = []
  function walk(dir: string) {
    if (!fs.existsSync(dir)) return
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        if (entry.name === 'node_modules' || entry.name === 'dist' || entry.name === '__tests__') continue
        walk(path.join(dir, entry.name))
        continue
      }
      if (!/\.(tsx?|jsx?)$/.test(entry.name)) continue
      // 跳过测试文件自身，避免误命中本测试中的字面量
      if (/\.(test|spec)\.tsx?$/.test(entry.name)) continue
      buckets.push(fs.readFileSync(path.join(dir, entry.name), 'utf-8'))
    }
  }
  walk(SRC_DIR)
  return buckets.join('\n\n---FILE---\n\n')
}

describe('frontend · V3 品牌一致性 (cross-source scan)', () => {
  const corpus = readCorpus()

  it('不再出现 V2 旧品牌"安心法务" / "安心智慧法务"', () => {
    expect(corpus).not.toMatch(/安心法务/)
    expect(corpus).not.toMatch(/安心智慧法务/)
  })

  it('不出现 V2 副标"让法律服务更简单" / "超级安心智能助手系统"', () => {
    expect(corpus).not.toContain('让法律服务更简单')
    expect(corpus).not.toContain('超级安心智能助手系统')
  })

  it('不残留 UniApp 路线相关字样（uni-mobile / @dcloudio）', () => {
    expect(corpus).not.toMatch(/uni-mobile/i)
    expect(corpus).not.toMatch(/@dcloudio/i)
  })

  it('Login 页保留 V3 8 大业务域定位文案', () => {
    const login = fs.readFileSync(path.join(SRC_DIR, 'pages', 'Login.tsx'), 'utf-8')
    expect(login).toMatch(/全链路 AI 经营助理/)
    expect(login).toMatch(/一个 App，搞定企业 8 大业务/)
    // 必须 import DOMAINS 元数据，避免被回退到硬编码字符串
    expect(login).toMatch(/from\s*['"]@\/lib\/domains['"]/)
  })

  it('Layout 顶部 navGroups 保留 V3 业务域映射 (accent 字段)', () => {
    const layout = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'Layout.tsx'),
      'utf-8',
    )
    // 4 个 navGroups 必须都标了 accent
    expect(layout).toMatch(/accent:\s*['"]operations['"]/)
    expect(layout).toMatch(/accent:\s*['"]legal['"]/)
    expect(layout).toMatch(/accent:\s*['"]growth['"]/)
    // active 态彩条用 --domain-${accent} CSS 变量
    expect(layout).toMatch(/hsl\(var\(--domain-/)
  })

  it('index.css 保留 8 个 --domain-* 浅色变量', () => {
    const css = fs.readFileSync(path.join(SRC_DIR, 'index.css'), 'utf-8')
    for (const id of [
      'legal',
      'finance',
      'tax',
      'compliance',
      'operations',
      'growth',
      'content',
      'global',
    ]) {
      expect(css).toMatch(new RegExp(`--domain-${id}:\\s*\\d`))
      expect(css).toMatch(new RegExp(`--domain-${id}-surface:\\s*\\d`))
    }
  })

  it('index.css 注释顶部明确品牌名为「安心智能助手」(V3)', () => {
    const css = fs.readFileSync(path.join(SRC_DIR, 'index.css'), 'utf-8')
    expect(css).toMatch(/安心智能助手/)
    expect(css).not.toMatch(/^[^\n]*安心法务/m)
  })

  // ===== V3 路由 & 顶栏入口守护（防止 DomainHomePage / Layout 入口被回退）=====

  it('App.tsx 必须注册 /domains 路由 → DomainHomePage', () => {
    const app = fs.readFileSync(path.join(SRC_DIR, 'App.tsx'), 'utf-8')
    // 懒加载声明
    expect(app).toMatch(/lazy\(\(\)\s*=>\s*import\(['"]@\/pages\/DomainHomePage['"]\)\)/)
    // 路由注册
    expect(app).toMatch(/<Route\s+path=["']domains["']\s+element=/)
  })

  it('Layout.tsx 必须含 /domains 顶栏入口按钮', () => {
    const layout = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'Layout.tsx'),
      'utf-8',
    )
    // 跳转到 /domains
    expect(layout).toMatch(/navigate\(['"]\/domains['"]\)/)
    // 用 LayoutGrid 图标
    expect(layout).toMatch(/icons\.LayoutGrid/)
    // 有"业务域"相关 aria 文案
    expect(layout).toMatch(/业务域/)
  })

  it('DomainHomePage 必须 import DomainGrid + DOMAINS 元数据', () => {
    const page = fs.readFileSync(
      path.join(SRC_DIR, 'pages', 'DomainHomePage.tsx'),
      'utf-8',
    )
    expect(page).toMatch(/from\s*['"]@\/components\/ui\/domain['"]/)
    expect(page).toMatch(/from\s*['"]@\/lib\/domains['"]/)
    expect(page).toMatch(/<DomainGrid/)
  })
})

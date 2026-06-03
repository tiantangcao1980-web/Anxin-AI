// V3 品牌一致性 + Reset 反向断链守护
//
// 2026-05 Reset：旧版守护 V3 token / 文案存在；新版加多个反向断言：
//   1. 禁止任何 --domain-* CSS 变量 / colors.domain.* utility 回归
//   2. 禁止 ui-design skill FORBIDDEN COLORS (violet/purple/indigo/fuchsia)
//   3. 禁止 ui-design skill FORBIDDEN FONTS (Inter/Roboto/Arial/Helvetica/system-ui)
//   4. 禁止任何 emoji 字符在组件源码中作 UI 图标
//   5. 保留：V3 文案必现 + Login + Layout V3 路径守护

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
      if (/\.(test|spec)\.tsx?$/.test(entry.name)) continue
      buckets.push(fs.readFileSync(path.join(dir, entry.name), 'utf-8'))
    }
  }
  walk(SRC_DIR)
  return buckets.join('\n\n---FILE---\n\n')
}

function readFile(rel: string): string {
  return fs.readFileSync(path.join(SRC_DIR, rel), 'utf-8')
}

describe('frontend · V3 品牌一致性 (cross-source scan)', () => {
  const corpus = readCorpus()

  it('不再出现 V2 旧品牌「安心法务」/「安心智慧法务」', () => {
    expect(corpus).not.toMatch(/安心法务/)
    expect(corpus).not.toMatch(/安心智慧法务/)
  })

  it('不出现 V2 旧副标「让法律服务更简单」/「超级安心智能助手系统」', () => {
    expect(corpus).not.toContain('让法律服务更简单')
    expect(corpus).not.toContain('超级安心智能助手系统')
  })

  it('不残留 UniApp 路线相关字样 (uni-mobile / @dcloudio)', () => {
    expect(corpus).not.toMatch(/uni-mobile/i)
    expect(corpus).not.toMatch(/@dcloudio/i)
  })
})

describe('frontend · Reset 反向断链守护 (违反即 fail)', () => {
  it('【Reset】index.css 不得回归任何 --domain-* CSS 变量', () => {
    const css = readFile('index.css')
    expect(css).not.toMatch(/--domain-(legal|finance|tax|compliance|operations|growth|content|global)\b/)
    expect(css).not.toMatch(/--domain-[a-z]+-surface\b/)
  })

  it('【Reset】tailwind.config.js 不得回归 colors.domain.* utility', () => {
    const cfg = fs.readFileSync(path.join(SRC_DIR, '..', 'tailwind.config.js'), 'utf-8')
    // 允许注释中提及（带 Reset 标记），但禁止实际 colors.domain 对象
    expect(cfg).not.toMatch(/colors:\s*{[^}]*\bdomain\s*:/s)
    // hsl(var(--domain-... 也禁止
    expect(cfg).not.toMatch(/hsl\(var\(--domain-/)
  })

  it('【Reset】index.css 不得回归 ui-design skill FORBIDDEN FONTS (Inter/Roboto/system-ui/-apple-system)', () => {
    const css = readFile('index.css')
    // 在 font-family 声明上下文中不得出现这些
    const fontDecls = css.match(/font-family\s*:\s*[^;]+/gi) ?? []
    for (const decl of fontDecls) {
      expect(decl).not.toMatch(/\bInter\b/)
      expect(decl).not.toMatch(/\bRoboto\b/)
      expect(decl).not.toMatch(/system-ui\b/)
      expect(decl).not.toMatch(/-apple-system\b/)
    }
  })

  it('【Reset】tailwind.config.js fontFamily 不得回归 FORBIDDEN FONTS', () => {
    const cfg = fs.readFileSync(path.join(SRC_DIR, '..', 'tailwind.config.js'), 'utf-8')
    const sansBlock = cfg.match(/sans\s*:\s*\[([\s\S]*?)\]/)
    if (sansBlock) {
      const body = sansBlock[1]
      expect(body).not.toMatch(/['"]Inter['"]/)
      expect(body).not.toMatch(/['"]Roboto['"]/)
      expect(body).not.toMatch(/['"]Arial['"]/)
      expect(body).not.toMatch(/['"]Helvetica( Neue)?['"]/)
      expect(body).not.toMatch(/['"]system-ui['"]/)
      expect(body).not.toMatch(/['"]-apple-system['"]/)
    }
  })

  it('【Reset】index.css 不得出现 ui-design FORBIDDEN COLORS (violet/purple/indigo/fuchsia) 作 design token', () => {
    const css = readFile('index.css')
    // hsl(270 ... ~ hsl(290 ...) 紫色 hue 范围
    // hsl(260 ... ~ hsl(280 ...) violet/indigo
    // 注意：AI 紫 hsl(262 ...) 是 DESIGN.md §2 原条款保留，仅 AI 生成态用
    // 故允许 --ai* 变量内的 262 色相，禁止其它变量名
    const lines = css.split('\n')
    for (const line of lines) {
      // 跳过 --ai-* 变量行（DESIGN.md §2 保留）
      if (/--ai[a-z-]*:/i.test(line)) continue
      // 跳过 --node-* 图谱节点色（业务隔离，DESIGN.md §6 保留 — 用于图算法 canvas）
      if (/--node-[a-z-]*:/i.test(line)) continue
      // 跳过 --primary 系（琥珀橙 hue 25）— hsl 25 不会落在 violet 范围
      // 检查紫色 hue 在 token 变量行
      if (/--[a-z-]+:\s*(260|261|262|263|264|265|266|267|268|269|270|271|272|273|274|275|276|277|278|279|280|281|282|283|284|285|286|287|288|289|290)\s+/.test(line)) {
        throw new Error(`Reset 反向断言失败：发现紫色 hue 在 design token 变量中：\n${line.trim()}`)
      }
    }
  })

  it('【Reset】frontend/src 业务组件源码不得出现 emoji 作 UI 图标', () => {
    // 仅检查 components/Layout/Login/WelcomeGuide/DomainHomePage 等业务 UI 文件
    const targets = [
      path.join(SRC_DIR, 'components', 'Layout.tsx'),
      path.join(SRC_DIR, 'components', 'WelcomeGuide.tsx'),
      path.join(SRC_DIR, 'components', 'ui', 'domain.tsx'),
      path.join(SRC_DIR, 'components', 'ui', 'DomainBreadcrumb.tsx'),
      path.join(SRC_DIR, 'pages', 'Login.tsx'),
      path.join(SRC_DIR, 'pages', 'DomainHomePage.tsx'),
      path.join(SRC_DIR, 'lib', 'domains.ts'),
    ]
    // 常见 UI emoji 黑名单
    const emojiRe = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u
    for (const file of targets) {
      if (!fs.existsSync(file)) continue
      const text = fs.readFileSync(file, 'utf-8')
      if (emojiRe.test(text)) {
        const match = text.match(emojiRe)
        throw new Error(`Reset 反向断言失败：${path.relative(SRC_DIR, file)} 含 emoji ${match?.[0]}（用 Lucide 替代）`)
      }
    }
  })
})

describe('frontend · V3 关键路径文案守护', () => {
  it('Login 页保留 V3 关键文案 + import DOMAINS 元数据', () => {
    const login = readFile('pages/Login.tsx')
    expect(login).toMatch(/为企业老板而做的 AI 工作台/)
    expect(login).toMatch(/一个 App 搞定企业 8 大业务/)
    expect(login).toMatch(/from\s*['"]@\/lib\/domains['"]/)
  })

  it('Layout 4 大 nav 保留 + /domains 入口保留 + 不再有 group.accent / item.domain', () => {
    const layout = readFile('components/Layout.tsx')
    expect(layout).toMatch(/navigate\(['"]\/domains['"]\)/)
    expect(layout).toMatch(/icons\.LayoutGrid/)
    expect(layout).toMatch(/业务域/)
    // Reset 反向：navGroups 不应再有 accent 字段
    expect(layout).not.toMatch(/accent\s*:\s*['"](legal|finance|tax|compliance|operations|growth|content|global)['"]/)
    // SidebarItem 不应再有 domain 字段
    expect(layout).not.toMatch(/{\s*path:\s*['"][^'"]+['"]\s*,\s*label:[^,]+,\s*icon:[^,]+,\s*[^}]*domain\s*:/)
  })

  it('App.tsx 必须保留 /domains 路由 + DomainHomePage lazy import', () => {
    const app = fs.readFileSync(path.join(SRC_DIR, 'App.tsx'), 'utf-8')
    expect(app).toMatch(/lazy\(\(\)\s*=>\s*import\(['"]@\/pages\/DomainHomePage['"]\)\)/)
    expect(app).toMatch(/<Route\s+path=["']domains["']\s+element=/)
  })

  it('DomainHomePage 必须 import DOMAINS 元数据', () => {
    const page = readFile('pages/DomainHomePage.tsx')
    expect(page).toMatch(/from\s*['"]@\/lib\/domains['"]/)
    expect(page).toMatch(/DOMAINS/)
  })

  it('index.css 注释顶部明确品牌名为「安心智能助手」(V3)', () => {
    const css = readFile('index.css')
    expect(css).toMatch(/安心智能助手/)
  })
})

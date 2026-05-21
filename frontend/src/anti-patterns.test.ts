/**
 * Editorial Luxury · 反模式工程守护（UI_GUIDELINES.md §8 自动化）
 *
 * 扫描 frontend/src/pages 全量 .tsx 文件，捕获散落反模式。
 * 比 brand-consistency.test.ts 更细 — 检查的是「散落的违规模式」而非「特定路径必现」。
 *
 * 当前策略：
 *   - 给出**容忍上限**（如「散落 text-2xl 不能超过 N 处」），随业务页改造逐步降低
 *   - 容忍上限基于审计基线（full-page-audit-2026-05-20.md）
 *   - 不允许引入新违规
 *
 * 后续每完成一个 Phase，上限应同步下调（commit message 说明降幅）
 */

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const PAGES_DIR = path.resolve(__dirname, 'pages')

function* walkTsxFiles(dir: string): Generator<string> {
  if (!fs.existsSync(dir)) return
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      yield* walkTsxFiles(path.join(dir, entry.name))
      continue
    }
    if (!/\.tsx?$/.test(entry.name)) continue
    if (/\.(test|spec)\.tsx?$/.test(entry.name)) continue
    yield path.join(dir, entry.name)
  }
}

function countMatchesInPages(regex: RegExp): { total: number; files: Array<{ file: string; count: number }> } {
  let total = 0
  const files: Array<{ file: string; count: number }> = []
  for (const file of walkTsxFiles(PAGES_DIR)) {
    const text = fs.readFileSync(file, 'utf-8')
    const matches = text.match(regex)
    const n = matches ? matches.length : 0
    if (n > 0) {
      total += n
      files.push({ file: path.relative(PAGES_DIR, file), count: n })
    }
  }
  files.sort((a, b) => b.count - a.count)
  return { total, files }
}

describe('frontend pages · Editorial Luxury 反模式守护', () => {
  // ── 字号/字重反模式 ──
  // 容忍上限基于审计基线 (2026-05-20)；每完成 Phase 应下调
  it('散落 text-2xl / text-3xl / text-4xl 数量不超过审计基线', () => {
    const { total, files } = countMatchesInPages(/\btext-(2xl|3xl|4xl)\b/g)
    if (total > 9) {
      throw new Error(
        `Editorial Luxury 反模式：散落 text-2xl/3xl/4xl 超过基线 9 处。当前 ${total} 处。\n` +
        `Top 命中：\n${files.slice(0, 5).map((f) => `  ${f.file}: ${f.count}`).join('\n')}\n` +
        `请使用 <EditorialPageHeader> 或 token (text-h1/h2/h3) 替代。`
      )
    }
    expect(total).toBeLessThanOrEqual(9)
  })

  it('散落 font-bold / font-extrabold / font-black 数量不超过审计基线', () => {
    const { total, files } = countMatchesInPages(/\bfont-(bold|extrabold|black)\b/g)
    if (total > 18) {
      throw new Error(
        `Editorial Luxury 反模式：散落 font-bold 超过基线 18 处。当前 ${total} 处。\n` +
        `Top 命中：\n${files.slice(0, 5).map((f) => `  ${f.file}: ${f.count}`).join('\n')}\n` +
        `请用 font-medium 替代。`
      )
    }
    expect(total).toBeLessThanOrEqual(18)
  })

  // ── 颜色违规 ──
  it('紫色 / violet / purple / indigo / fuchsia utility 出现 0 次', () => {
    const { total, files } = countMatchesInPages(
      /\b(bg|text|border|ring)-(violet|purple|indigo|fuchsia)(-\d{2,3})?\b/g
    )
    if (total > 0) {
      throw new Error(
        `ui-design FORBIDDEN COLORS：发现紫色族 utility ${total} 处。\n` +
        files.slice(0, 5).map((f) => `  ${f.file}: ${f.count}`).join('\n')
      )
    }
    expect(total).toBe(0)
  })

  it('Hex 硬编码 #xxxxxx 在 pages 业务代码中容忍数 ≤ 9（PDF 模板）', () => {
    const { total, files } = countMatchesInPages(/#[0-9A-Fa-f]{6}\b/g)
    // 当前基线：admin/AdminAudit.tsx 含 9 处 PDF 模板 hex
    if (total > 9) {
      throw new Error(
        `Editorial Luxury 反模式：Hex 硬编码超过基线 9 处。当前 ${total} 处。\n` +
        files.slice(0, 5).map((f) => `  ${f.file}: ${f.count}`).join('\n') +
        `\n请改用 token（CSS variables / tailwind colors）。`
      )
    }
    expect(total).toBeLessThanOrEqual(9)
  })

  // ── 字体违规 ──
  it('pages/ 业务代码不得出现 Inter / system-ui / Helvetica 等 FORBIDDEN FONTS', () => {
    const { total, files } = countMatchesInPages(
      /["'](Inter|Roboto|Arial|Helvetica( Neue)?|system-ui|-apple-system|BlinkMacSystemFont)["']/g
    )
    if (total > 0) {
      throw new Error(
        `ui-design FORBIDDEN FONTS：发现 ${total} 处违禁字体引用。\n` +
        files.slice(0, 5).map((f) => `  ${f.file}: ${f.count}`).join('\n')
      )
    }
    expect(total).toBe(0)
  })

  // ── Emoji 反模式 ──
  it('pages/ 业务代码 emoji 字面值容忍数 ≤ 16（基线 2026-05-20）', () => {
    // 检查 emoji 区段：1F300-1F9FF / 2600-26FF / 2700-27BF
    // 基线：admin/AdminIntegrations(7) + v3/TasksPage(4) + admin/AdminAudit(3) + CaseMarket(1) + LawyerDashboard(1) = 16
    // 每完成 Phase 应同步下调基线（commit 注明降幅）
    const emojiRe = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu
    let total = 0
    const files: Array<{ file: string; count: number }> = []
    for (const file of walkTsxFiles(PAGES_DIR)) {
      const text = fs.readFileSync(file, 'utf-8')
      const matches = text.match(emojiRe)
      const n = matches ? matches.length : 0
      if (n > 0) {
        total += n
        files.push({ file: path.relative(PAGES_DIR, file), count: n })
      }
    }
    files.sort((a, b) => b.count - a.count)
    if (total > 16) {
      throw new Error(
        `Editorial Luxury 反模式：emoji 字面值超过基线 16 处。当前 ${total} 处。\n` +
        files.slice(0, 5).map((f) => `  ${f.file}: ${f.count}`).join('\n') +
        `\n请用 lucide 图标替代。`
      )
    }
    expect(total).toBeLessThanOrEqual(16)
  })

  // ── 模板使用统计（信息性，不强制）──
  it('PageContainer / ListPageTemplate / DetailPageTemplate 等模板覆盖率统计', () => {
    let usingPageContainer = 0
    let usingNewTemplate = 0
    let totalPages = 0
    for (const file of walkTsxFiles(PAGES_DIR)) {
      totalPages++
      const text = fs.readFileSync(file, 'utf-8')
      if (/PageContainer|CenterLayout/.test(text)) usingPageContainer++
      if (/ListPageTemplate|DetailPageTemplate|FormPageTemplate|DashboardTemplate|AdminTableTemplate/.test(text)) {
        usingNewTemplate++
      }
    }
    // 信息性输出，不 fail
    console.log(
      `📊 模板覆盖率：` +
      `PageContainer/CenterLayout = ${usingPageContainer}/${totalPages} (${Math.round((usingPageContainer / totalPages) * 100)}%) | ` +
      `Editorial PageTemplate = ${usingNewTemplate}/${totalPages} (${Math.round((usingNewTemplate / totalPages) * 100)}%)`
    )
    expect(totalPages).toBeGreaterThan(60)
  })
})

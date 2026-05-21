// V3 design-tokens 守护 (Reset 后)
//
// 2026-05 Reset：禁止任何 $color-domain-* / 违禁紫色 / emoji 回归

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { domainMeta, miniProgramTheme, riskTier, type DomainId } from './design-tokens'

describe('mini-program · design-tokens (Reset)', () => {
  it('品牌主色 #F97316（飞书风琥珀橙 — 2026-05-22 蓝图）', () => {
    expect(miniProgramTheme.brandPrimary).toBe('#F97316')
  })

  it('风险三档保留（与 frontend 跨端对齐）', () => {
    expect(riskTier.high.color).toMatch(/^#[0-9A-F]{6}$/i)
    expect(riskTier.medium.color).toMatch(/^#[0-9A-F]{6}$/i)
    expect(riskTier.low.color).toMatch(/^#[0-9A-F]{6}$/i)
  })

  it('domainMeta 包含 8 个业务域', () => {
    const expected: DomainId[] = [
      'legal', 'finance', 'tax', 'compliance',
      'operations', 'growth', 'content', 'global',
    ]
    expect(Object.keys(domainMeta)).toEqual(expected)
  })

  it('【Reset】domainMeta 不得包含 color / surface 字段', () => {
    for (const meta of Object.values(domainMeta)) {
      const metaAny = meta as unknown as Record<string, unknown>
      expect(metaAny.color).toBeUndefined()
      expect(metaAny.surface).toBeUndefined()
    }
  })

  it('【Reset】design-tokens.ts 源码不得出现 8 域专属 hex 色码', () => {
    const file = path.resolve(__dirname, 'design-tokens.ts')
    const text = fs.readFileSync(file, 'utf-8')
    // 排除与 warning(#E2A311) / info(#1F6FD4) 状态色重叠
    const forbidden = [
      '#5C7F3E', '#E84F2E',
      '#7D4FCC', // 违禁紫
      '#17AAC3', '#DE3F88', '#1768A1',
    ]
    for (const hex of forbidden) {
      expect(text.toUpperCase()).not.toContain(hex.toUpperCase())
    }
  })

  it('【Reset】design-tokens.scss 不得回归 $color-domain-* 变量', () => {
    const scss = fs.readFileSync(
      path.resolve(__dirname, 'design-tokens.scss'),
      'utf-8',
    )
    // 允许注释（含 Reset 标记），但禁止 SCSS 变量声明
    expect(scss).not.toMatch(/^\$color-domain-/m)
  })

  it('【Reset】DomainBadge 源码不得包含 emoji 字面值', () => {
    const file = path.resolve(__dirname, '..', 'components', 'DomainBadge', 'index.tsx')
    const text = fs.readFileSync(file, 'utf-8')
    const emojiRe = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u
    expect(emojiRe.test(text)).toBe(false)
  })

  it('UniApp 退场后无 uni-mobile / dcloud 残留', () => {
    const ts = fs.readFileSync(path.resolve(__dirname, 'design-tokens.ts'), 'utf-8')
    expect(ts).not.toMatch(/uni-mobile/i)
    expect(ts).not.toMatch(/dcloud/i)
  })
})

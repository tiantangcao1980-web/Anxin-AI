// 跨端 design-tokens 完整性 smoke 测试
//
// 目标：防止 token 文件被误删 / 被改回旧 V2 值 / 与 frontend 漂移。
// 这些断言在 commercial-readiness-gate 的快速门禁里会被 mini-program test 步骤拉到。

import { describe, expect, it } from 'vitest'
import {
  aiSemantic,
  domain,
  miniProgramTheme,
  riskTier,
  type DomainId,
} from './design-tokens'

describe('mini-program design tokens · V3 一致性', () => {
  it('品牌主色仍是琥珀橙 #D4A574 (与 frontend / mobile 跨端对齐)', () => {
    expect(miniProgramTheme.brandPrimary).toBe('#D4A574')
    expect(miniProgramTheme.brandPrimaryDark).toBe('#B8864E')
  })

  it('表面/文本层级 5 档完整且互不重复', () => {
    const values = [
      miniProgramTheme.background,
      miniProgramTheme.surface,
      miniProgramTheme.textPrimary,
      miniProgramTheme.textSecondary,
      miniProgramTheme.textTertiary,
      miniProgramTheme.border,
    ]
    expect(new Set(values).size).toBe(values.length)
  })

  it('风险三档导出齐全，每档自带 surface 底色 + 中文标签', () => {
    const tiers: Array<keyof typeof riskTier> = ['high', 'medium', 'low']
    for (const t of tiers) {
      expect(riskTier[t].color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(riskTier[t].surface).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(riskTier[t].labelZh.length).toBeGreaterThan(0)
    }
  })

  it('AI 语义色三态（思考 / 建议 / 引用）导出齐全', () => {
    expect(aiSemantic.thinking.color).toBeTruthy()
    expect(aiSemantic.suggestion.color).toBeTruthy()
    expect(aiSemantic.citation.color).toBeTruthy()
  })

  it('V3 8 大业务域齐全，按固定顺序枚举', () => {
    const expected: DomainId[] = [
      'legal',
      'finance',
      'tax',
      'compliance',
      'operations',
      'growth',
      'content',
      'global',
    ]
    expect(Object.keys(domain)).toEqual(expected)
  })

  it('每个业务域都有 color + surface + 中文 + 英文标签', () => {
    const expectedLabels: Record<DomainId, string> = {
      legal: '法务',
      finance: '财务',
      tax: '税务',
      compliance: '合规',
      operations: '经营管理',
      growth: '调研获客',
      content: '内容产出',
      global: '出海跨境',
    }
    for (const [id, meta] of Object.entries(domain)) {
      expect(meta.color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(meta.surface).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(meta.labelZh).toBe(expectedLabels[id as DomainId])
      expect(meta.labelEn.length).toBeGreaterThan(0)
    }
  })

  it('业务域色与品牌主色不重叠（域是分类，不抢品牌识别）', () => {
    for (const meta of Object.values(domain)) {
      expect(meta.color.toLowerCase()).not.toBe(miniProgramTheme.brandPrimary.toLowerCase())
    }
  })

  it('UniApp 退场后不应在 token 注释或导出中残留 uni-mobile 字样', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const file = path.resolve(__dirname, 'design-tokens.ts')
    const text = await fs.readFile(file, 'utf-8')
    expect(text).not.toMatch(/uni-mobile/i)
    expect(text).not.toMatch(/uni-app/i)
    expect(text).not.toMatch(/dcloud/i)
  })
})

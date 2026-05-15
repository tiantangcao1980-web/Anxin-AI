// -*- coding: utf-8 -*-
//
// 跨端 design tokens 完整性 smoke 测试（与 mini-program/src/styles/design-tokens.test.ts 对称）
//
// 目标：防止 mobile 端 V3 token 被误删 / 被改回 V2 蓝色或法务专用配色 / 跨端漂移。
// 失败信号优先于 runtime — 这些断言会在 `commercial-readiness-gate` 的 mobile test 步骤被拉到。

import { describe, expect, it } from 'vitest'
import {
  domain,
  darkTheme,
  lightTheme,
  palette,
  type DomainId,
} from './colors'

describe('mobile theme/colors · V3 一致性', () => {
  it('品牌主色仍是琥珀橙 #D4A574（跨端对齐 frontend / mini-program）', () => {
    expect(palette.primary).toBe('#D4A574')
    expect(palette.primary500).toBe('#C18C56')
  })

  it('AI 语义三态（思考 / 建议 / 引用）导出齐全', () => {
    expect(palette.aiThinking).toBeTruthy()
    expect(palette.aiSuggestion).toBeTruthy()
    expect(palette.aiCitation).toBeTruthy()
    // 每个语义色都有配套的 surface 底
    expect(palette.aiThinkingSurface).toBeTruthy()
    expect(palette.aiSuggestionSurface).toBeTruthy()
    expect(palette.aiCitationSurface).toBeTruthy()
  })

  it('风险三档完整 + 与状态 success/error 不重叠', () => {
    expect(palette.riskHigh).toMatch(/^#[0-9A-Fa-f]{6}$/)
    expect(palette.riskMedium).toMatch(/^#[0-9A-Fa-f]{6}$/)
    expect(palette.riskLow).toMatch(/^#[0-9A-Fa-f]{6}$/)
    // 风险 ≠ 状态：高风险 ≠ error
    expect(palette.riskHigh.toLowerCase()).not.toBe(palette.error.toLowerCase())
    expect(palette.riskMedium.toLowerCase()).not.toBe(palette.warning.toLowerCase())
  })

  it('置信度三档完整', () => {
    expect(palette.confidenceHigh).toBeTruthy()
    expect(palette.confidenceMedium).toBeTruthy()
    expect(palette.confidenceLow).toBeTruthy()
  })

  it('V3 8 大业务域齐全且按固定顺序导出', () => {
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

  it('每个业务域都有 color + surface + zh + en 标签', () => {
    const expectedLabels: Record<DomainId, { zh: string; en: string }> = {
      legal:      { zh: '法务',     en: 'Legal' },
      finance:    { zh: '财务',     en: 'Finance' },
      tax:        { zh: '税务',     en: 'Tax' },
      compliance: { zh: '合规',     en: 'Compliance' },
      operations: { zh: '经营管理', en: 'Operations' },
      growth:     { zh: '调研获客', en: 'Growth' },
      content:    { zh: '内容产出', en: 'Content' },
      global:     { zh: '出海跨境', en: 'Global' },
    }
    for (const [id, meta] of Object.entries(domain)) {
      expect(meta.color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(meta.surface).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(meta.labelZh).toBe(expectedLabels[id as DomainId].zh)
      expect(meta.labelEn).toBe(expectedLabels[id as DomainId].en)
    }
  })

  it('业务域色不与品牌主色重叠（保持分类语义独立）', () => {
    for (const meta of Object.values(domain)) {
      expect(meta.color.toLowerCase()).not.toBe(palette.primary.toLowerCase())
    }
  })

  it('lightTheme 和 darkTheme 都暴露所有 V3 新增字段', () => {
    const v3Fields: Array<keyof typeof lightTheme> = [
      'aiThinking',
      'aiSuggestion',
      'aiCitation',
      'riskHigh',
      'riskMedium',
      'riskLow',
      'confidenceHigh',
      'confidenceMedium',
      'confidenceLow',
    ]
    for (const f of v3Fields) {
      expect(lightTheme[f]).toBeTruthy()
      expect(darkTheme[f]).toBeTruthy()
    }
  })

  it('darkTheme 与 lightTheme 在「显示色」字段上必须不同（暗色生效）', () => {
    expect(darkTheme.background).not.toBe(lightTheme.background)
    expect(darkTheme.text).not.toBe(lightTheme.text)
    expect(darkTheme.surface).not.toBe(lightTheme.surface)
  })

  it('UniApp 退场后 colors.ts 不应残留 uni-mobile / DCloud 字样', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const file = path.resolve(__dirname, 'colors.ts')
    const text = await fs.readFile(file, 'utf-8')
    expect(text).not.toMatch(/uni-mobile/i)
    expect(text).not.toMatch(/uni-app/i)
    expect(text).not.toMatch(/dcloud/i)
  })
})

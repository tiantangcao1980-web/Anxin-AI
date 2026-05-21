// -*- coding: utf-8 -*-
//
// V3 colors 守护测试 (Reset 后)
//
// 2026-05 Reset：旧版守护 8 域 color/surface 不漂移。
// 新版反向：禁止任何 domain.* 高饱和色 / 紫色 / Inter 等违禁项回归。

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { domainMeta, darkTheme, lightTheme, palette, type DomainId } from './colors'

describe('mobile theme/colors · V3 (Reset)', () => {
  it('品牌主色 #F97316（飞书风琥珀橙 — 2026-05-22 蓝图）', () => {
    expect(palette.primary).toBe('#F97316')
    expect(palette.primary500).toBe('#F97316')
  })

  it('AI 语义三态 + 风险三档 + 置信度三档保留', () => {
    expect(palette.aiThinking).toBeTruthy()
    expect(palette.aiSuggestion).toBeTruthy()
    expect(palette.aiCitation).toBeTruthy()
    expect(palette.riskHigh).toBeTruthy()
    expect(palette.riskMedium).toBeTruthy()
    expect(palette.riskLow).toBeTruthy()
    expect(palette.confidenceHigh).toBeTruthy()
    expect(palette.confidenceMedium).toBeTruthy()
    expect(palette.confidenceLow).toBeTruthy()
  })

  it('domainMeta 包含 8 个业务域，按固定顺序', () => {
    const expected: DomainId[] = [
      'legal', 'finance', 'tax', 'compliance',
      'operations', 'growth', 'content', 'global',
    ]
    expect(Object.keys(domainMeta)).toEqual(expected)
  })

  it('【Reset】domainMeta 不得包含 color / surface 字段（曾被违禁紫色污染）', () => {
    for (const meta of Object.values(domainMeta)) {
      const metaAny = meta as unknown as Record<string, unknown>
      expect(metaAny.color).toBeUndefined()
      expect(metaAny.surface).toBeUndefined()
    }
  })

  it('【Reset】colors.ts 源码不得出现 8 域专属 hex 色码（避免软回退）', () => {
    const file = path.resolve(__dirname, 'colors.ts')
    const text = fs.readFileSync(file, 'utf-8')
    // 旧 8 域色（含违禁紫）— 排除与状态色 / 风险三档色重叠的值：
    //   - #E2A311 同 warning, #1F6FD4 同 info, #FCF3DA 同 riskMediumSoft
    //     这些是 DESIGN.md §2 保留的语义色，不视为域色违规
    const forbiddenDomainHex = [
      '#5C7F3E', '#EBF1E2', '#E0EAF8',
      '#E84F2E', '#FCE6DF',
      '#7D4FCC', '#ECE3F8', // ← 违禁紫（必删）
      '#17AAC3', '#DCF3F6', '#DE3F88', '#FBE0EC',
      '#1768A1', '#DDEBF4',
    ]
    for (const hex of forbiddenDomainHex) {
      expect(text.toUpperCase()).not.toContain(hex.toUpperCase())
    }
  })

  it('lightTheme / darkTheme V3 字段完备 + 暗色生效', () => {
    expect(lightTheme.text).toBeTruthy()
    expect(darkTheme.background).not.toBe(lightTheme.background)
  })

  it('UniApp 退场后 colors.ts 无残留 uni-mobile / dcloud', () => {
    const file = path.resolve(__dirname, 'colors.ts')
    const text = fs.readFileSync(file, 'utf-8')
    expect(text).not.toMatch(/uni-mobile/i)
    expect(text).not.toMatch(/dcloud/i)
  })
})

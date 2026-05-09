import { describe, expect, it } from 'vitest'

import {
  QUICK_QUERY_MAX_CHARS,
  normalizeQuickQueryInput,
  resolveLocalQuickQueryAnswer,
  shouldUseLocalQuickQuery,
} from './quickQueryModel'

describe('quickQueryModel', () => {
  it('normalizes non-empty questions without changing intent', () => {
    expect(normalizeQuickQueryInput('  帮我判断这个合同风险  ')).toEqual({
      ok: true,
      value: '帮我判断这个合同风险',
    })
  })

  it('rejects empty and oversized questions', () => {
    expect(normalizeQuickQueryInput('   ')).toEqual({
      ok: false,
      error: '请输入问题',
    })
    expect(normalizeQuickQueryInput('x'.repeat(QUICK_QUERY_MAX_CHARS + 1))).toMatchObject({
      ok: false,
    })
  })

  it('uses local LLM only for desktop top-secret and hybrid modes', () => {
    expect(shouldUseLocalQuickQuery('top-secret', true)).toBe(true)
    expect(shouldUseLocalQuickQuery('hybrid', true)).toBe(true)
    expect(shouldUseLocalQuickQuery('cloud', true)).toBe(false)
    expect(shouldUseLocalQuickQuery('top-secret', false)).toBe(false)
  })

  it('normalizes local LLM answers and rejects empty responses', () => {
    expect(
      resolveLocalQuickQueryAnswer({
        success: true,
        source: 'local',
        model: 'qwen2.5:7b',
        message: '  先核验主体资质。 ',
      }),
    ).toEqual({
      ok: true,
      answer: '先核验主体资质。',
      source: 'local',
      model: 'qwen2.5:7b',
    })

    expect(resolveLocalQuickQueryAnswer(null)).toEqual({
      ok: false,
      error: '本地模型暂未返回内容',
    })
  })
})

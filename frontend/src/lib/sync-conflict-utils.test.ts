import { describe, expect, it } from 'vitest'

import {
  buildMergedConflictDraft,
  formatConflictData,
  parseConflictMergeDraft,
} from './sync-conflict-utils'

describe('sync conflict utils', () => {
  it('formats conflict data as stable pretty JSON', () => {
    expect(formatConflictData({ title: '合同', status: 'draft' })).toBe(
      '{\n  "title": "合同",\n  "status": "draft"\n}'
    )
  })

  it('builds a local-priority merge draft over remote data', () => {
    const draft = buildMergedConflictDraft(
      { title: '本地', status: 'draft' },
      { title: '云端', reviewer: 'alice' },
    )

    expect(JSON.parse(draft)).toEqual({
      title: '本地',
      status: 'draft',
      reviewer: 'alice',
    })
  })

  it('accepts only JSON objects for manual merge payloads', () => {
    expect(parseConflictMergeDraft('{"title":"合并"}')).toEqual({
      ok: true,
      data: { title: '合并' },
    })
    expect(parseConflictMergeDraft('[1,2]')).toEqual({
      ok: false,
      message: '合并内容必须是 JSON 对象',
    })
    expect(parseConflictMergeDraft('{bad')).toEqual({
      ok: false,
      message: '合并内容不是合法 JSON',
    })
  })
})

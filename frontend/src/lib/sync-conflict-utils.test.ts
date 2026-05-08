import { describe, expect, it } from 'vitest'

import {
  buildMergedConflictDraft,
  countChangedConflictFields,
  formatConflictData,
  formatConflictEntityType,
  formatConflictPreview,
  parseConflictMergeDraft,
  summarizeConflictData,
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

  it('summarizes changed fields for non-technical conflict previews', () => {
    const summary = summarizeConflictData(
      {
        title: '本地合同',
        status: 'draft',
        unchanged: 'same',
        attachments: ['a.pdf', 'b.pdf'],
      },
      {
        title: '云端合同',
        status: 'reviewing',
        unchanged: 'same',
        attachments: ['a.pdf'],
      },
    )

    expect(summary).toEqual([
      {
        key: 'attachments',
        label: 'attachments',
        localPreview: '2 项',
        remotePreview: '1 项',
      },
      {
        key: 'status',
        label: '状态',
        localPreview: 'draft',
        remotePreview: 'reviewing',
      },
      {
        key: 'title',
        label: '标题',
        localPreview: '本地合同',
        remotePreview: '云端合同',
      },
    ])
    expect(countChangedConflictFields(
      { title: '本地', status: 'draft' },
      { title: '云端', status: 'draft' },
    )).toBe(1)
  })

  it('formats entity labels and compact value previews', () => {
    expect(formatConflictEntityType('contract')).toBe('合同')
    expect(formatConflictEntityType('sync_log')).toBe('Sync Log')
    expect(formatConflictPreview({ title: '事项摘要', extra: true })).toBe('事项摘要')
    expect(formatConflictPreview({ id: 1, nested: { ok: true } })).toBe('2 个字段')
  })
})

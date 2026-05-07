import { describe, expect, it } from 'vitest'
import { getExternalSourceUrl, getSourceDocumentId, getSourceLabel, splitSourceContent } from './source-preview-utils'

describe('knowledge source preview utils', () => {
  it('prefers explicit document ids before falling back to source ids', () => {
    expect(getSourceDocumentId({ doc_id: 'doc-1', id: 'chunk-1' })).toBe('doc-1')
    expect(getSourceDocumentId({ id: 'doc-2' })).toBe('doc-2')
  })

  it('opens external source urls only when no document id is available', () => {
    expect(getExternalSourceUrl({ source_url: '/source/law.html' })).toBe('/source/law.html')
    expect(getExternalSourceUrl({ doc_id: 'doc-1', source_url: '/source/law.html' })).toBeNull()
  })

  it('builds a stable visible label for source chips', () => {
    expect(getSourceLabel({ title: '劳动合同法' }, 0)).toBe('劳动合同法')
    expect(getSourceLabel({ source: '法规库' }, 1)).toBe('法规库')
    expect(getSourceLabel({}, 2)).toBe('来源 3')
  })

  it('splits source content around the exact anchor for UI highlighting', () => {
    expect(splitSourceContent('甲方应当依法支付工资。', '依法支付工资')).toEqual([
      { text: '甲方应当', highlighted: false },
      { text: '依法支付工资', highlighted: true },
      { text: '。', highlighted: false },
    ])
  })
})

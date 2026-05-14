/**
 * I3 (2026-05-14): ApprovalLinkInline extractApprovalIds 单测
 */
import { describe, expect, test } from 'vitest'

import { extractApprovalIds } from './ApprovalLinkInline'

describe('extractApprovalIds', () => {
  test('extracts approval id from 中文 reject 文本', () => {
    const content = '该操作需要人工审批, 已自动创建工单 ap_abc123def456, 审批通过后请重试。'
    expect(extractApprovalIds(content)).toEqual(['ap_abc123def456'])
  })

  test('extracts approval id from English variant', () => {
    const content = 'Approval ID: short-uuid-12'
    expect(extractApprovalIds(content)).toEqual(['short-uuid-12'])
  })

  test('extracts multiple distinct ids', () => {
    const content = '工单 abc12345 已建, 同时也创建了工单 xyz98765 等待审批'
    expect(extractApprovalIds(content)).toEqual(['abc12345', 'xyz98765'])
  })

  test('deduplicates identical ids', () => {
    const content = '工单 dup_id_xx 重复出现工单 dup_id_xx'
    expect(extractApprovalIds(content)).toEqual(['dup_id_xx'])
  })

  test('returns empty for unrelated content', () => {
    expect(extractApprovalIds('普通聊天消息, 没有工单引用')).toEqual([])
  })

  test('handles empty / null content', () => {
    expect(extractApprovalIds('')).toEqual([])
  })

  test('ignores too-short ids (under 6 chars)', () => {
    expect(extractApprovalIds('工单 abc')).toEqual([])
  })
})

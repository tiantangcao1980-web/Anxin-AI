import { describe, expect, it } from 'vitest'

import { summarizeFileDropQueueReport } from './desktopFileDropEvents'
import type { FileDropQueueReport } from './tauri-bridge'

const queuedContract = {
  task_id: 'task-1',
  file_name: '租赁合同.pdf',
  task_type: 'contract_review',
  action_label: '合同审查',
}

describe('desktopFileDropEvents', () => {
  it('summarizes one queued file with the intended desktop action', () => {
    const report: FileDropQueueReport = {
      queued: [queuedContract],
      unsupported: [],
    }

    expect(summarizeFileDropQueueReport(report)).toEqual({
      title: '已加入待分析队列',
      description: '租赁合同.pdf · 合同审查',
      variant: 'success',
    })
  })

  it('summarizes mixed queued and unsupported drops without leaking local paths', () => {
    const report: FileDropQueueReport = {
      queued: [queuedContract],
      unsupported: [{ file_name: 'archive.zip', reason: '暂不支持 .zip 文件' }],
    }

    const summary = summarizeFileDropQueueReport(report)

    expect(summary).toEqual({
      title: '部分文件已加入队列',
      description: '1 个入队，1 个暂不支持',
      variant: 'warning',
    })
    expect(JSON.stringify(summary)).not.toContain('/Users/')
  })

  it('returns warning text when no dropped file can be queued', () => {
    const report: FileDropQueueReport = {
      queued: [],
      unsupported: [{ file_name: 'photo.png', reason: '暂不支持 .png 文件' }],
    }

    expect(summarizeFileDropQueueReport(report)).toEqual({
      title: '文件未入队',
      description: 'photo.png · 暂不支持 .png 文件',
      variant: 'warning',
    })
  })

  it('skips empty reports', () => {
    expect(summarizeFileDropQueueReport({ queued: [], unsupported: [] })).toBeNull()
  })
})

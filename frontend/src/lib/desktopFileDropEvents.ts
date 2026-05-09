import type { FileDropQueueReport, FileDropQueuedTask, UnsupportedFileDrop } from './tauri-bridge'

export type FileDropQueueToastVariant = 'success' | 'warning' | 'info'

export interface DesktopDragDropPayload {
  type: string
  paths?: unknown
}

export interface FileDropQueueToastSummary {
  title: string
  description: string
  variant: FileDropQueueToastVariant
}

function formatQueuedFile(task: FileDropQueuedTask): string {
  return `${task.file_name} · ${task.action_label}`
}

function formatUnsupportedFile(file: UnsupportedFileDrop): string {
  return `${file.file_name} · ${file.reason}`
}

export function summarizeFileDropQueueReport(report: FileDropQueueReport): FileDropQueueToastSummary | null {
  const queuedCount = report.queued.length
  const unsupportedCount = report.unsupported.length

  if (queuedCount === 0 && unsupportedCount === 0) {
    return null
  }

  if (queuedCount > 0 && unsupportedCount === 0) {
    return {
      title: '已加入待分析队列',
      description: queuedCount === 1 ? formatQueuedFile(report.queued[0]) : `${queuedCount} 个文件已入队`,
      variant: 'success',
    }
  }

  if (queuedCount > 0 && unsupportedCount > 0) {
    return {
      title: '部分文件已加入队列',
      description: `${queuedCount} 个入队，${unsupportedCount} 个暂不支持`,
      variant: 'warning',
    }
  }

  return {
    title: '文件未入队',
    description: unsupportedCount === 1 ? formatUnsupportedFile(report.unsupported[0]) : `${unsupportedCount} 个文件暂不支持`,
    variant: 'warning',
  }
}

export function extractDesktopFileDropPaths(payload: DesktopDragDropPayload | null | undefined): string[] {
  if (!payload || payload.type !== 'drop' || !Array.isArray(payload.paths)) {
    return []
  }

  return payload.paths
    .filter((path): path is string => typeof path === 'string')
    .map((path) => path.trim())
    .filter(Boolean)
}

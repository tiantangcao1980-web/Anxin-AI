export function formatConflictData(data: Record<string, unknown>): string {
  return JSON.stringify(data ?? {}, null, 2)
}

export interface ConflictFieldSummary {
  key: string
  label: string
  localPreview: string
  remotePreview: string
}

const ENTITY_LABELS: Record<string, string> = {
  artifact: '成果',
  case: '案件',
  contract: '合同',
  conversation: '会话',
  document: '文档',
  message: '消息',
  setting: '设置',
  task: '任务',
}

const FIELD_LABELS: Record<string, string> = {
  amount: '金额',
  assignee_id: '负责人',
  content: '内容',
  description: '描述',
  due_date: '截止时间',
  name: '名称',
  status: '状态',
  summary: '摘要',
  title: '标题',
  updated_at: '更新时间',
}

export function buildMergedConflictDraft(
  localData: Record<string, unknown>,
  remoteData: Record<string, unknown>,
): string {
  return formatConflictData({
    ...remoteData,
    ...localData,
  })
}

export function parseConflictMergeDraft(value: string): {
  ok: boolean
  data?: Record<string, unknown>
  message?: string
} {
  try {
    const parsed = JSON.parse(value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { ok: false, message: '合并内容必须是 JSON 对象' }
    }
    return { ok: true, data: parsed as Record<string, unknown> }
  } catch {
    return { ok: false, message: '合并内容不是合法 JSON' }
  }
}

export function formatConflictEntityType(entityType: string): string {
  const normalized = entityType.trim().toLowerCase()
  if (ENTITY_LABELS[normalized]) return ENTITY_LABELS[normalized]
  return entityType
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function summarizeConflictData(
  localData: Record<string, unknown>,
  remoteData: Record<string, unknown>,
  limit = 4,
): ConflictFieldSummary[] {
  const keys = Array.from(new Set([
    ...Object.keys(localData ?? {}),
    ...Object.keys(remoteData ?? {}),
  ])).sort((left, right) => left.localeCompare(right))

  return keys
    .filter((key) => !conflictValuesEqual(localData?.[key], remoteData?.[key]))
    .slice(0, Math.max(1, limit))
    .map((key) => ({
      key,
      label: FIELD_LABELS[key] ?? key,
      localPreview: formatConflictPreview(localData?.[key]),
      remotePreview: formatConflictPreview(remoteData?.[key]),
    }))
}

export function countChangedConflictFields(
  localData: Record<string, unknown>,
  remoteData: Record<string, unknown>,
): number {
  const keys = new Set([
    ...Object.keys(localData ?? {}),
    ...Object.keys(remoteData ?? {}),
  ])
  return Array.from(keys).filter((key) => !conflictValuesEqual(localData?.[key], remoteData?.[key])).length
}

export function formatConflictPreview(value: unknown): string {
  if (value === null || value === undefined) return '空'
  if (typeof value === 'string') return truncatePreview(value.trim() || '空文本')
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return `${value.length} 项`
  if (typeof value === 'object') {
    const objectValue = value as Record<string, unknown>
    const title = objectValue.title ?? objectValue.name ?? objectValue.summary
    if (typeof title === 'string' && title.trim()) return truncatePreview(title.trim())
    return `${Object.keys(objectValue).length} 个字段`
  }
  return truncatePreview(String(value))
}

function conflictValuesEqual(left: unknown, right: unknown): boolean {
  return JSON.stringify(left ?? null) === JSON.stringify(right ?? null)
}

function truncatePreview(value: string, maxLength = 72): string {
  if (value.length <= maxLength) return value
  return `${value.slice(0, maxLength - 3)}...`
}

export function formatConflictData(data: Record<string, unknown>): string {
  return JSON.stringify(data ?? {}, null, 2)
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

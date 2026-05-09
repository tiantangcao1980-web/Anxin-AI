import type { AppMode, LocalLLMResponse } from '@/lib/tauri-bridge'

export const QUICK_QUERY_MAX_CHARS = 2000
export const QUICK_QUERY_AUTO_HIDE_MS = 1500

export const QUICK_QUERY_SYSTEM_PROMPT =
  '你是安心法务桌面快问助手。回答要简洁、可执行，优先指出法律风险、下一步动作和需要补充的材料。'

export type QuickQueryValidation =
  | { ok: true; value: string }
  | { ok: false; error: string }

export type QuickQueryAnswer =
  | { ok: true; answer: string; source: string; model: string }
  | { ok: false; error: string }

export function normalizeQuickQueryInput(value: string): QuickQueryValidation {
  const trimmed = value.trim()
  if (!trimmed) {
    return { ok: false, error: '请输入问题' }
  }
  if (trimmed.length > QUICK_QUERY_MAX_CHARS) {
    return { ok: false, error: `快问最多支持 ${QUICK_QUERY_MAX_CHARS} 字` }
  }
  return { ok: true, value: trimmed }
}

export function shouldUseLocalQuickQuery(mode: AppMode | null, tauriRuntime: boolean): boolean {
  return tauriRuntime && (mode === 'top-secret' || mode === 'hybrid')
}

export function resolveLocalQuickQueryAnswer(response: LocalLLMResponse | null): QuickQueryAnswer {
  const answer = response?.message?.trim()
  if (!response?.success || !answer) {
    return { ok: false, error: '本地模型暂未返回内容' }
  }

  return {
    ok: true,
    answer,
    source: response.source || 'local',
    model: response.model || 'local-model',
  }
}

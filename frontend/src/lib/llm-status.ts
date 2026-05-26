/**
 * LLM 配置状态检测
 *
 * 用途：
 *  - 首启 OnboardingWizard 在 step 3 完成检测
 *  - 全局 LlmNotConfiguredBanner 决定是否挂载
 *  - /chat /v3/personas/* 等智能体入口在未配置时显示占位
 *
 * 关联：docs/plans/2026-05-22-desktop-bootstrap.md §4.3
 */

import { llmApi } from '@/lib/api'

export type LlmProvider =
  | 'openai'
  | 'anthropic'
  | 'qwen'
  | 'deepseek'
  | 'hunyuan'
  | 'ollama'
  | 'lmstudio'
  | 'custom'
  | string // 兼容后端未来扩展

export interface LlmStatus {
  /** 是否已配置至少 1 个可用 provider 且设了默认 */
  configured: boolean
  /** 是否有任意本地 provider（Ollama / LMStudio） */
  hasLocal: boolean
  /** 是否有任意远程 provider（OpenAI / 通义 / 等） */
  hasRemote: boolean
  /** 配置总数 */
  total: number
  /** 默认 provider 名称（若已设） */
  defaultProvider?: string
  /** 默认模型名称（若已设） */
  defaultModel?: string
  /** 检测过程中的错误（鉴权失败 / 网络等） */
  error?: string
}

const LOCAL_PROVIDERS: ReadonlySet<string> = new Set(['ollama', 'lmstudio'])

/** 静默检测当前 LLM 配置状态。错误不抛，转为 error 字段。 */
export async function checkLlmStatus(): Promise<LlmStatus> {
  try {
    const configsRes = await llmApi.listConfigs({ is_active: true, page_size: 50 })
    const items = configsRes.items ?? []
    const total = items.length

    if (total === 0) {
      return {
        configured: false,
        hasLocal: false,
        hasRemote: false,
        total: 0,
      }
    }

    let defaultProvider: string | undefined
    let defaultModel: string | undefined
    try {
      const def = await llmApi.getDefaultConfig('llm')
      defaultProvider = def?.provider
      // LLMConfig 在不同版本字段名可能是 model / model_name；兼容
      defaultModel =
        (def as { model_name?: string; model?: string })?.model_name ??
        (def as { model_name?: string; model?: string })?.model
    } catch {
      // 没有默认配置 → configured 仍 false
      defaultProvider = undefined
    }

    const hasLocal = items.some((c) => LOCAL_PROVIDERS.has(c.provider))
    const hasRemote = items.some((c) => !LOCAL_PROVIDERS.has(c.provider))

    return {
      configured: total > 0 && !!defaultProvider,
      hasLocal,
      hasRemote,
      total,
      defaultProvider,
      defaultModel,
    }
  } catch (err) {
    return {
      configured: false,
      hasLocal: false,
      hasRemote: false,
      total: 0,
      error: err instanceof Error ? err.message : '未知错误',
    }
  }
}

/** 判断给定 provider 是否本地 LLM */
export function isLocalProvider(provider: string): boolean {
  return LOCAL_PROVIDERS.has(provider)
}

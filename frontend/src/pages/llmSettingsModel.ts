import type { LLMConfigCreate } from '@/lib/api'

export type LlmConfigForm = {
  name: string
  provider: string
  model_name: string
  api_key: string
  api_base_url: string
  config_type: string
  max_tokens: number
  temperature: number
  is_default: boolean
}

export function buildLlmConfigSavePayload(
  form: LlmConfigForm,
  options: { editing: boolean },
): LLMConfigCreate {
  const payload: LLMConfigCreate = {
    name: form.name.trim(),
    provider: form.provider,
    model_name: form.model_name.trim(),
    config_type: form.config_type,
    api_base_url: form.api_base_url.trim(),
    max_tokens: form.max_tokens,
    temperature: form.temperature,
    is_default: form.is_default,
  }

  const apiKey = form.api_key.trim()
  if (apiKey) {
    payload.api_key = apiKey
  }

  return payload
}

export function getLlmCredentialSummary(config: { api_key_masked?: string | null } | null): string {
  return config?.api_key_masked ? `已保存 ${config.api_key_masked}` : '未保存密钥'
}

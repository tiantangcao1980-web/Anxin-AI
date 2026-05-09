import { describe, expect, it } from 'vitest'
import { buildLlmConfigSavePayload, getLlmCredentialSummary } from './llmSettingsModel'

const baseForm = {
  name: '  org-default-qwen  ',
  provider: 'openai',
  model_name: '  gpt-4o-mini  ',
  api_key: '',
  api_base_url: '  https://api.example.test/v1  ',
  config_type: 'llm',
  max_tokens: 4096,
  temperature: 0.7,
  is_default: true,
}

describe('llmSettingsModel', () => {
  it('omits api_key when editing metadata without replacing the credential', () => {
    const payload = buildLlmConfigSavePayload(baseForm, { editing: true })

    expect(payload).not.toHaveProperty('api_key')
    expect(payload.name).toBe('org-default-qwen')
    expect(payload.model_name).toBe('gpt-4o-mini')
    expect(payload.api_base_url).toBe('https://api.example.test/v1')
  })

  it('includes api_key only for explicit create and replacement credentials', () => {
    expect(buildLlmConfigSavePayload(baseForm, { editing: false })).not.toHaveProperty('api_key')
    expect(
      buildLlmConfigSavePayload({ ...baseForm, api_key: ' sk-create-secret ' }, { editing: false }).api_key,
    ).toBe('sk-create-secret')
    expect(
      buildLlmConfigSavePayload({ ...baseForm, api_key: ' sk-live-replacement ' }, { editing: true }).api_key,
    ).toBe('sk-live-replacement')
  })

  it('summarizes persisted credentials with masked values only', () => {
    expect(getLlmCredentialSummary({ api_key_masked: 'sk-a...7890' })).toBe('已保存 sk-a...7890')
    expect(getLlmCredentialSummary({ api_key_masked: 'sk-a...7890' })).not.toContain('live-secret')
    expect(getLlmCredentialSummary(null)).toBe('未保存密钥')
  })
})

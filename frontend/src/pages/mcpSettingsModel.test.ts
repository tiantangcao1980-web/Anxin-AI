import { describe, expect, it } from 'vitest'
import { buildMcpSavePayload, getPersistedEnvKeys, maskMcpEnvValue } from './mcpSettingsModel'

const baseForm = {
  name: 'approved-search',
  description: 'approved connector',
  type: 'stdio',
  command: 'npx',
  args: ['-y', '@modelcontextprotocol/server-brave-search'],
  env: { BRAVE_API_KEY: 'sandbox-secret-value' },
  url: '',
  is_enabled: true,
}

describe('mcpSettingsModel', () => {
  it('omits env when editing metadata without replacing credentials', () => {
    const payload = buildMcpSavePayload(baseForm, { editing: true, replaceEnv: false })

    expect(payload).not.toHaveProperty('env')
    expect(payload.name).toBe('approved-search')
  })

  it('includes env for create and explicit credential replacement', () => {
    expect(buildMcpSavePayload(baseForm, { editing: false, replaceEnv: false }).env).toEqual(baseForm.env)
    expect(buildMcpSavePayload(baseForm, { editing: true, replaceEnv: true }).env).toEqual(baseForm.env)
  })

  it('uses env_keys as persisted credential evidence without exposing values', () => {
    expect(getPersistedEnvKeys({ env_keys: ['BRAVE_API_KEY'] })).toEqual(['BRAVE_API_KEY'])
    expect(maskMcpEnvValue('sandbox-secret-value')).toBe('已填写')
    expect(maskMcpEnvValue('')).toBe('待填写')
    expect(maskMcpEnvValue('sandbox-secret-value')).not.toContain('sandbox')
  })
})

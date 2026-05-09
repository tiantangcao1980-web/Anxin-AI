import type { SkillConnectorConfig, SkillConnectorConfigPayload } from '@/lib/api'

export type SkillConnectorCredentialMode = 'preserve' | 'replace' | 'clear'

export type SkillConnectorFormState = {
  skill_name: string
  connector_name: string
  connector_type: string
  endpoint_url: string
  auth_type: string
  credentials_text: string
  credential_mode: SkillConnectorCredentialMode
  is_enabled: boolean
}

export const defaultSkillConnectorForm: SkillConnectorFormState = {
  skill_name: 'contract-review',
  connector_name: '',
  connector_type: 'http_api',
  endpoint_url: '',
  auth_type: 'api_key',
  credentials_text: '',
  credential_mode: 'replace',
  is_enabled: true,
}

export function connectorToForm(config: SkillConnectorConfig): SkillConnectorFormState {
  return {
    skill_name: config.skill_name,
    connector_name: config.connector_name,
    connector_type: config.connector_type || 'http_api',
    endpoint_url: config.endpoint_url ?? '',
    auth_type: config.auth_type || 'api_key',
    credentials_text: '',
    credential_mode: 'preserve',
    is_enabled: config.is_enabled,
  }
}

export function parseConnectorCredentials(text: string): Record<string, string> {
  const credentials: Record<string, string> = {}
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const separatorIndex = line.includes('=') ? line.indexOf('=') : line.indexOf(':')
    if (separatorIndex <= 0) continue
    const key = line.slice(0, separatorIndex).trim()
    const value = line.slice(separatorIndex + 1).trim()
    if (key && value) credentials[key] = value
  }
  return credentials
}

export function buildSkillConnectorPayload(
  form: SkillConnectorFormState,
  options: { editing: boolean },
): SkillConnectorConfigPayload {
  const payload: SkillConnectorConfigPayload = {
    skill_name: form.skill_name.trim(),
    connector_name: form.connector_name.trim(),
    connector_type: form.connector_type.trim() || 'http_api',
    endpoint_url: form.endpoint_url.trim() || null,
    auth_type: form.auth_type.trim() || 'api_key',
    is_enabled: form.is_enabled,
  }

  if (!options.editing || form.credential_mode === 'replace') {
    const credentials = parseConnectorCredentials(form.credentials_text)
    if (Object.keys(credentials).length > 0) {
      payload.credentials = credentials
    }
  }

  if (options.editing && form.credential_mode === 'clear') {
    payload.credentials = {}
  }

  return payload
}

export function summarizeConnectorCredentials(config: Pick<SkillConnectorConfig, 'credential_keys'>): string {
  const keys = config.credential_keys ?? []
  if (keys.length === 0) return '未保存凭据'
  return `已保存 ${keys.length} 个键：${keys.join(', ')}`
}

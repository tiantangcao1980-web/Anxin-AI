import { describe, expect, it } from 'vitest'

import {
  buildSkillConnectorPayload,
  connectorToForm,
  defaultSkillConnectorForm,
  parseConnectorCredentials,
  summarizeConnectorCredentials,
} from './skillConnectorSettingsModel'

describe('skillConnectorSettingsModel', () => {
  it('parses newline credentials and ignores empty or malformed lines', () => {
    expect(parseConnectorCredentials(' API_KEY = sk-live \n# comment\nCLIENT_SECRET: value\nbroken')).toEqual({
      API_KEY: 'sk-live',
      CLIENT_SECRET: 'value',
    })
  })

  it('omits credentials when editing metadata in preserve mode', () => {
    const payload = buildSkillConnectorPayload(
      {
        ...defaultSkillConnectorForm,
        skill_name: 'contract-review',
        connector_name: 'court-data',
        endpoint_url: 'https://court.example.test/api',
        credentials_text: 'API_KEY=sk-should-not-send',
        credential_mode: 'preserve',
      },
      { editing: true },
    )

    expect(payload).not.toHaveProperty('credentials')
    expect(payload.endpoint_url).toBe('https://court.example.test/api')
  })

  it('sends credentials only for create, replace, or clear actions', () => {
    expect(
      buildSkillConnectorPayload(
        {
          ...defaultSkillConnectorForm,
          connector_name: 'court-data',
          credentials_text: 'API_KEY=sk-create',
        },
        { editing: false },
      ).credentials,
    ).toEqual({ API_KEY: 'sk-create' })

    expect(
      buildSkillConnectorPayload(
        {
          ...defaultSkillConnectorForm,
          connector_name: 'court-data',
          credentials_text: 'TOKEN=sk-replace',
          credential_mode: 'replace',
        },
        { editing: true },
      ).credentials,
    ).toEqual({ TOKEN: 'sk-replace' })

    expect(
      buildSkillConnectorPayload(
        {
          ...defaultSkillConnectorForm,
          connector_name: 'court-data',
          credential_mode: 'clear',
        },
        { editing: true },
      ).credentials,
    ).toEqual({})
  })

  it('creates an edit form without exposing saved credential values', () => {
    const form = connectorToForm({
      id: 'connector-1',
      org_id: 'org-1',
      skill_name: 'contract-review',
      connector_name: 'court-data',
      connector_type: 'http_api',
      endpoint_url: 'https://court.example.test/api',
      auth_type: 'api_key',
      credential_keys: ['API_KEY'],
      is_enabled: true,
    })

    expect(form.credentials_text).toBe('')
    expect(form.credential_mode).toBe('preserve')
    expect(summarizeConnectorCredentials({ credential_keys: ['API_KEY', 'CLIENT_SECRET'] })).toBe(
      '已保存 2 个键：API_KEY, CLIENT_SECRET',
    )
  })
})

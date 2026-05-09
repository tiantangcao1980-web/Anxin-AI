import type { McpServerCreate } from '@/lib/api'

export function maskMcpEnvValue(value: string | null | undefined): string {
  return value ? '已填写' : '待填写'
}

export function buildMcpSavePayload(
  form: McpServerCreate,
  options: { editing: boolean; replaceEnv: boolean }
): Partial<McpServerCreate> {
  const payload: Partial<McpServerCreate> = {
    name: form.name,
    description: form.description,
    type: form.type,
    command: form.command,
    args: form.args,
    url: form.url,
    is_enabled: form.is_enabled,
  }

  if (!options.editing || options.replaceEnv) {
    payload.env = form.env ?? {}
  }

  return payload
}

export function getPersistedEnvKeys(server: { env_keys?: string[]; env?: Record<string, string> } | null): string[] {
  if (!server) return []
  if (Array.isArray(server.env_keys)) return server.env_keys
  return Object.keys(server.env ?? {})
}

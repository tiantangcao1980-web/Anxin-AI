import type { WorkspaceArtifact } from './store'

export function normalizeWorkspaceArtifactEvent(
  rawArtifact: unknown,
  fallbackId: string,
  now = Date.now(),
): WorkspaceArtifact | null {
  if (!rawArtifact || typeof rawArtifact !== 'object') return null
  const artifact = rawArtifact as Record<string, any>
  const metadata = artifact.metadata && typeof artifact.metadata === 'object'
    ? artifact.metadata as Record<string, any>
    : {}
  const content = artifact.content && typeof artifact.content === 'object'
    ? artifact.content as Record<string, any>
    : {}
  const createdAt = typeof artifact.created_at === 'string'
    ? Date.parse(artifact.created_at)
    : Number(artifact.createdAt || now)

  return {
    id: String(artifact.id || fallbackId),
    artifactType: String(artifact.artifact_type || artifact.artifactType || 'agent_runtime_summary'),
    title: String(artifact.title || '长任务运行摘要'),
    content,
    metadata,
    createdAt: Number.isFinite(createdAt) ? createdAt : now,
    source: String(metadata.source || artifact.source || 'agent-runtime'),
  }
}

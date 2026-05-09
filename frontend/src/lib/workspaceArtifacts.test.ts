import { describe, expect, it } from 'vitest'

import { normalizeWorkspaceArtifactEvent } from './workspaceArtifacts'

describe('workspaceArtifacts', () => {
  it('normalizes runtime artifact events into cacheable workspace artifacts', () => {
    const artifact = normalizeWorkspaceArtifactEvent(
      {
        id: 'runtime-task-1',
        artifact_type: 'agent_runtime_summary',
        title: '长任务运行摘要',
        created_at: '2026-05-09T12:00:00.000Z',
        content: {
          summary: '合同风险摘要已生成',
          timeline: [{ event: 'artifact_created', status: 'ready_for_review' }],
        },
        metadata: {
          source: 'legal_workforce.process_task_streaming',
          runtime_generated: true,
        },
      },
      'fallback-id',
      1,
    )

    expect(artifact).toMatchObject({
      id: 'runtime-task-1',
      artifactType: 'agent_runtime_summary',
      title: '长任务运行摘要',
      source: 'legal_workforce.process_task_streaming',
    })
    expect(artifact?.createdAt).toBe(Date.parse('2026-05-09T12:00:00.000Z'))
    expect(artifact?.content.timeline[0].status).toBe('ready_for_review')
  })

  it('rejects malformed events instead of adding fake artifacts', () => {
    expect(normalizeWorkspaceArtifactEvent(null, 'fallback-id', 1)).toBeNull()
    expect(normalizeWorkspaceArtifactEvent('not-an-artifact', 'fallback-id', 1)).toBeNull()
  })
})

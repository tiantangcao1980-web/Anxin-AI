import type { Page, Route } from '@playwright/test'

type AuthSeed = {
  role: string
  userId?: string
  name?: string
  email?: string
  expired?: boolean
  /** V2: 可选的客户端类型（needer=需求方端 / provider=服务方端）。
   *  不传时让 ProtectedRoute 按 role 推断：lawyer/partner/paralegal/platform_lawyer → provider。 */
  primary_client?: 'needer' | 'provider'
}

export type MockOptions = {
  auth?: Partial<AuthSeed>
  contracts?: {
    list?: unknown
    create?: unknown
    review?: unknown
  }
  documents?: {
    list?: unknown
    get?: unknown
    analyze?: unknown
  }
  tasks?: {
    list?: unknown
    transition?: unknown
  }
  lawyer?: {
    consultation?: unknown
    lawyers?: unknown
    delegation?: unknown
  }
  knowledge?: {
    bases?: unknown
    ragQuery?: unknown
    search?: unknown
    document?: unknown
    stats?: unknown
    documents?: unknown
  }
  graph?: {
    overview?: unknown
    search?: unknown
    types?: unknown
    detail?: unknown
    subgraph?: unknown
  }
  mcp?: {
    servers?: unknown
  }
  llm?: {
    providers?: Record<string, unknown>
    configs?: { items?: Array<Record<string, unknown>>; total?: number; page?: number; page_size?: number }
    testConnection?: unknown
    testSavedConfig?: unknown
    onCreate?: (body: Record<string, unknown>) => void
    onUpdate?: (body: Record<string, unknown>) => void
  }
  collaboration?: {
    sessions?: unknown
    session?: unknown
    collaborators?: unknown
    snapshots?: unknown
    restore?: unknown
  }
  agentApprovals?: {
    list?: unknown
    auditEvents?: unknown
    auditExport?: unknown
    workspaceArtifacts?: {
      list?: unknown
      create?: unknown
      update?: unknown
      export?: unknown
    }
    pendingCount?: unknown
    capabilityRoutes?: {
      list?: unknown
      update?: unknown
    }
    approve?: unknown
    reject?: unknown
    revoke?: unknown
    workspaceControl?: unknown
  }
  skillGovernance?: {
    list?: unknown
    enabled?: unknown
    create?: unknown
    auditEvents?: unknown
    auditExport?: unknown
    eval?: unknown
    approve?: unknown
    grayRelease?: unknown
    rollback?: unknown
    connectors?: {
      list?: { items?: Array<Record<string, unknown>>; total?: number }
      create?: unknown
      update?: unknown
      delete?: unknown
      onCreate?: (body: Record<string, unknown>) => void
      onUpdate?: (body: Record<string, unknown>) => void
    }
  }
  harness?: {
    tools?: unknown
    agentTools?: unknown
  }
  remoteControl?: {
    status?: unknown
    auditEvents?: unknown
    routeToken?: unknown
    cancelCommand?: unknown
  }
}

function createMockToken(role: string, userId = 'e2e-user', expired = false) {
  const encodeBase64Url = (value: string) =>
    Buffer.from(value, 'utf8').toString('base64url')

  const header = encodeBase64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = encodeBase64Url(
    JSON.stringify({
      sub: userId,
      role,
      exp: expired
        ? Math.floor(Date.now() / 1000) - 60
        : Math.floor(Date.now() / 1000) + 60 * 60,
    }),
  )

  return `${header}.${payload}.signature`
}

function buildUnified(data: unknown) {
  return {
    code: 0,
    data,
    message: 'ok',
    request_id: 'e2e-request',
  }
}

async function fulfillJson(route: Route, data: unknown) {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(data),
  })
}

export async function installApiMocks(page: Page, options: MockOptions = {}) {
  let llmConfigState = options.llm?.configs ?? {
    items: [
      {
        id: 'llm-e2e-1',
        name: '组织默认模型',
        provider: 'openai',
        config_type: 'llm',
        model_name: 'gpt-4o-mini',
        api_base_url: 'https://api.example.test/v1',
        api_key_masked: 'sk-a...7890',
        max_tokens: 4096,
        temperature: 0.7,
        top_p: 1,
        frequency_penalty: 0,
        presence_penalty: 0,
        is_active: true,
        is_default: true,
        context_length: 4096,
        extra_params: {},
        total_calls: 12,
        total_tokens: 2048,
        avg_latency: 230,
        created_at: '2026-05-09T10:00:00Z',
        updated_at: '2026-05-09T10:00:00Z',
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  }
  let capabilityRoutePolicyState = options.agentApprovals?.capabilityRoutes?.list ?? {
    items: [
      {
        id: 'route-browser-fill',
        org_id: 'org-e2e',
        route_key: 'browser-fill',
        route_type: 'browser',
        provider: 'browser-use',
        risk_level: 'l3',
        status: 'enabled',
        allowed_consumers: ['owner-agent'],
        allowed_scopes: ['browser:read', 'browser:fill'],
        policy: { required_feature: 'browser_automation', requires_approval: true },
        token_ttl_seconds: 900,
        created_at: '2026-05-08T10:00:00Z',
        updated_at: '2026-05-08T10:00:00Z',
      },
    ],
    total: 1,
  }
  let skillConnectorState = options.skillGovernance?.connectors?.list ?? {
    items: [
      {
        id: 'skill-connector-e2e-1',
        org_id: 'org-e2e',
        skill_name: 'contract-review',
        connector_name: 'court-data',
        connector_type: 'http_api',
        endpoint_url: 'https://court.example.test/api',
        auth_type: 'api_key',
        credential_keys: ['API_KEY', 'CLIENT_SECRET'],
        is_enabled: true,
        created_by: 'e2e-admin',
        updated_by: 'e2e-admin',
        created_at: '2026-05-09T10:00:00Z',
        updated_at: '2026-05-09T10:00:00Z',
      },
    ],
    total: 1,
  }

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())

    if (pathname.endsWith('/auth/login') && request.method() === 'POST') {
      const role = options.auth?.role ?? 'admin'
      const userId = options.auth?.userId ?? 'e2e-admin'
      const accessToken = createMockToken(role, userId)
      return fulfillJson(
        route,
        buildUnified({
          access_token: accessToken,
          refresh_token: 'e2e-refresh-token',
          token_type: 'bearer',
          user: {
            id: userId,
            email: options.auth?.email ?? `${role}@anxinai.com`,
            name: options.auth?.name ?? 'E2E User',
            role,
            primary_client: options.auth?.primary_client,
          },
        }),
      )
    }

    if (pathname.endsWith('/auth/me') && request.method() === 'GET') {
      const role = options.auth?.role ?? 'admin'
      const userId = options.auth?.userId ?? 'e2e-admin'
      return fulfillJson(
        route,
        buildUnified({
          id: userId,
          email: options.auth?.email ?? `${role}@anxinai.com`,
          name: options.auth?.name ?? 'E2E User',
          role,
          primary_client: options.auth?.primary_client,
        }),
      )
    }

    if (pathname.endsWith('/skill-governance/enabled') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.enabled ?? {
            skill_name: 'contract-review',
            enabled_version: '1.0.0',
            enabled: true,
          },
        ),
      )
    }

    if (pathname.endsWith('/skill-governance/connectors') && request.method() === 'GET') {
      return fulfillJson(route, buildUnified(skillConnectorState))
    }

    if (pathname.endsWith('/skill-governance/connectors') && request.method() === 'POST') {
      const body = JSON.parse(request.postData() || '{}') as Record<string, unknown>
      options.skillGovernance?.connectors?.onCreate?.(body)
      const credentialKeys = Object.keys((body.credentials as Record<string, string> | undefined) ?? {})
      const created = {
        id: 'skill-connector-e2e-created',
        org_id: 'org-e2e',
        skill_name: body.skill_name ?? 'contract-review',
        connector_name: body.connector_name ?? 'new-connector',
        connector_type: body.connector_type ?? 'http_api',
        endpoint_url: body.endpoint_url ?? null,
        auth_type: body.auth_type ?? 'api_key',
        credential_keys: credentialKeys,
        is_enabled: body.is_enabled ?? true,
        created_by: 'e2e-admin',
        updated_by: 'e2e-admin',
        created_at: '2026-05-09T10:10:00Z',
        updated_at: '2026-05-09T10:10:00Z',
      }
      skillConnectorState = {
        items: [created, ...(skillConnectorState.items ?? [])],
        total: (skillConnectorState.total ?? 0) + 1,
      }
      return fulfillJson(route, buildUnified(options.skillGovernance?.connectors?.create ?? created))
    }

    if (/\/skill-governance\/connectors\/[^/]+$/.test(pathname) && request.method() === 'PUT') {
      const id = decodeURIComponent(pathname.split('/').pop() ?? '')
      const body = JSON.parse(request.postData() || '{}') as Record<string, unknown>
      options.skillGovernance?.connectors?.onUpdate?.(body)
      const current = (skillConnectorState.items ?? []).find((item) => item.id === id) ?? {
        id,
        org_id: 'org-e2e',
        skill_name: body.skill_name ?? 'contract-review',
        connector_name: body.connector_name ?? 'connector',
        connector_type: 'http_api',
        endpoint_url: null,
        auth_type: 'api_key',
        credential_keys: [],
        is_enabled: true,
      }
      const updated = {
        ...current,
        ...body,
        credential_keys: 'credentials' in body
          ? Object.keys((body.credentials as Record<string, string> | undefined) ?? {})
          : current.credential_keys,
        updated_at: '2026-05-09T10:12:00Z',
      }
      skillConnectorState = {
        items: (skillConnectorState.items ?? []).map((item) => (item.id === id ? updated : item)),
        total: skillConnectorState.total ?? 1,
      }
      return fulfillJson(route, buildUnified(options.skillGovernance?.connectors?.update ?? updated))
    }

    if (/\/skill-governance\/connectors\/[^/]+$/.test(pathname) && request.method() === 'DELETE') {
      const id = decodeURIComponent(pathname.split('/').pop() ?? '')
      skillConnectorState = {
        items: (skillConnectorState.items ?? []).filter((item) => item.id !== id),
        total: Math.max((skillConnectorState.total ?? 1) - 1, 0),
      }
      return fulfillJson(route, buildUnified(options.skillGovernance?.connectors?.delete ?? { deleted: true }))
    }

    if (pathname.endsWith('/skill-governance/proposals') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.list ?? {
            items: [
              {
                id: 'skill-e2e-1',
                org_id: 'org-e2e',
                skill_name: 'contract-review',
                current_version: '1.0.0',
                proposed_version: '1.1.0',
                source: 'workspace:e2e',
                created_by: 'employee-risk-owner',
                created_by_role: 'employee',
                risk_level: 'high',
                status: 'draft',
                eval_results: {},
                created_at: '2026-05-08T10:00:00Z',
                updated_at: '2026-05-08T10:00:00Z',
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
          },
        ),
      )
    }

    if (pathname.endsWith('/skill-governance/proposals') && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.create ?? {
            id: 'skill-e2e-created',
            org_id: 'org-e2e',
            skill_name: 'contract-review',
            current_version: '1.1.0',
            proposed_version: '1.2.0',
            source: 'workspace:manual-proposal',
            created_by: 'e2e-admin',
            created_by_role: 'admin',
            risk_level: 'medium',
            status: 'draft',
            eval_results: {},
            created_at: '2026-05-08T10:06:00Z',
            updated_at: '2026-05-08T10:06:00Z',
          },
        ),
      )
    }

    if (/\/skill-governance\/proposals\/[^/]+\/audit-events$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.auditEvents ?? {
            items: [
              {
                id: 'skill-audit-e2e-request',
                org_id: 'org-e2e',
                proposal_id: 'skill-e2e-1',
                actor: 'employee-risk-owner',
                action: 'skill_evolution.proposal.create',
                status: 'success',
                reason_code: 'draft_created',
                resource_snapshot: {
                  proposal_id: 'skill-e2e-1',
                  skill_name: 'contract-review',
                  status: 'draft',
                },
                metadata: { created_by_role: 'employee' },
                created_at: '2026-05-08T10:01:00Z',
              },
            ],
            total: 1,
          },
        ),
      )
    }

    if (/\/skill-governance\/proposals\/[^/]+\/audit-export$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.auditExport ?? {
            schema_version: 'skill_governance_audit_export.v1',
            generated_at: '2026-05-08T10:05:00Z',
            proposal: {
              id: 'skill-e2e-1',
              org_id: 'org-e2e',
              skill_name: 'contract-review',
              current_version: '1.0.0',
              proposed_version: '1.1.0',
              source: 'workspace:e2e',
              created_by: 'employee-risk-owner',
              created_by_role: 'employee',
              risk_level: 'high',
              status: 'draft',
              eval_results: {},
              created_at: '2026-05-08T10:00:00Z',
              updated_at: '2026-05-08T10:00:00Z',
            },
            audit_events: [
              {
                id: 'skill-audit-e2e-request',
                org_id: 'org-e2e',
                proposal_id: 'skill-e2e-1',
                actor: 'employee-risk-owner',
                action: 'skill_evolution.proposal.create',
                status: 'success',
                reason_code: 'draft_created',
                created_at: '2026-05-08T10:01:00Z',
              },
            ],
            total: 1,
            limit: 500,
          },
        ),
      )
    }

    if (/\/skill-governance\/proposals\/[^/]+\/eval$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.eval ?? {
            id: 'skill-e2e-1',
            org_id: 'org-e2e',
            skill_name: 'contract-review',
            current_version: '1.0.0',
            proposed_version: '1.1.0',
            source: 'workspace:e2e',
            created_by: 'employee-risk-owner',
            created_by_role: 'employee',
            risk_level: 'high',
            status: 'evaluated',
            eval_results: {
              offline_eval: true,
              permission_regression: true,
              prompt_injection: true,
              privacy_mode: true,
              audit_log: true,
            },
            created_at: '2026-05-08T10:00:00Z',
            updated_at: '2026-05-08T10:04:00Z',
          },
        ),
      )
    }

    if (/\/skill-governance\/proposals\/[^/]+\/approve$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.approve ?? {
            id: 'skill-e2e-2',
            org_id: 'org-e2e',
            skill_name: 'tax-risk',
            current_version: '2.0.0',
            proposed_version: '2.1.0',
            source: 'workspace:e2e',
            created_by: 'employee-risk-owner',
            created_by_role: 'employee',
            risk_level: 'high',
            status: 'approved',
            eval_results: {
              offline_eval: true,
              permission_regression: true,
              prompt_injection: true,
              privacy_mode: true,
              audit_log: true,
            },
            approved_by: 'e2e-admin',
            approver_role: 'admin',
            created_at: '2026-05-08T10:00:00Z',
            updated_at: '2026-05-08T10:05:00Z',
          },
        ),
      )
    }

    if (/\/skill-governance\/proposals\/[^/]+\/gray-release$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.grayRelease ?? {
            id: 'skill-e2e-3',
            org_id: 'org-e2e',
            skill_name: 'mcp-browser-use',
            current_version: '0.2.0',
            proposed_version: '0.3.0',
            source: 'workspace:e2e',
            created_by: 'employee-risk-owner',
            created_by_role: 'employee',
            risk_level: 'high',
            status: 'gray_released',
            gray_percentage: 100,
            eval_results: {
              offline_eval: true,
              permission_regression: true,
              prompt_injection: true,
              privacy_mode: true,
              audit_log: true,
            },
            created_at: '2026-05-08T10:00:00Z',
            updated_at: '2026-05-08T10:06:00Z',
          },
        ),
      )
    }

    if (/\/skill-governance\/proposals\/[^/]+\/rollback$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.skillGovernance?.rollback ?? {
            id: 'skill-e2e-3',
            org_id: 'org-e2e',
            skill_name: 'mcp-browser-use',
            current_version: '0.2.0',
            proposed_version: '0.3.0',
            source: 'workspace:e2e',
            created_by: 'employee-risk-owner',
            created_by_role: 'employee',
            risk_level: 'high',
            status: 'rolled_back',
            rollback_reason: 'rollback requested in workspace',
            eval_results: {
              offline_eval: true,
              permission_regression: true,
              prompt_injection: true,
              privacy_mode: true,
              audit_log: true,
            },
            created_at: '2026-05-08T10:00:00Z',
            updated_at: '2026-05-08T10:07:00Z',
          },
        ),
      )
    }

    if (pathname.endsWith('/agent-approvals/pending/count') && request.method() === 'GET') {
      return fulfillJson(route, buildUnified(options.agentApprovals?.pendingCount ?? { pending: 1 }))
    }

    if (pathname.endsWith('/agent-approvals/capability-routes') && request.method() === 'GET') {
      return fulfillJson(route, buildUnified(capabilityRoutePolicyState))
    }

    if (/\/agent-approvals\/capability-routes\/[^/]+$/.test(pathname) && request.method() === 'PATCH') {
      const routeKey = decodeURIComponent(pathname.split('/').pop() ?? '')
      const patch = JSON.parse(request.postData() || '{}') as Record<string, unknown>
      const list = capabilityRoutePolicyState as { items?: Array<Record<string, unknown>>; total?: number }
      const current = list.items?.find((item) => item.route_key === routeKey) ?? {
        id: `route-${routeKey}`,
        org_id: 'org-e2e',
        route_key: routeKey,
        route_type: 'custom',
        risk_level: 'l1',
        status: 'enabled',
        allowed_consumers: [],
        allowed_scopes: [],
        policy: {},
        token_ttl_seconds: 900,
      }
      const updated = {
        ...current,
        ...patch,
        updated_at: '2026-05-08T10:08:00Z',
      }
      capabilityRoutePolicyState = {
        items: (list.items ?? [current]).map((item) => (item.route_key === routeKey ? updated : item)),
        total: list.total ?? 1,
      }
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.capabilityRoutes?.update ?? {
            allowed: true,
            reason_code: 'updated',
            human_message: '能力路由策略已更新',
            revoked_lease_count: patch.status === 'disabled' ? 1 : 0,
            audit_event_id: 'audit-route-policy-e2e',
            route: updated,
          },
        ),
      )
    }

    if (pathname.endsWith('/agent-approvals') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.list ?? {
            items: [
              {
                id: 'approval-e2e-1',
                org_id: 'org-e2e',
                route_id: 'route-browser-control',
                requested_by: 'employee-risk-owner',
                action_type: 'browser.remote_control',
                risk_level: 'high',
                status: 'pending',
                payload: {
                  target: 'desktop-runtime',
                  reason: '远程执行高风险桌面动作',
                },
                expires_at: '2026-05-08T10:30:00Z',
                created_at: '2026-05-08T10:00:00Z',
                updated_at: '2026-05-08T10:00:00Z',
              },
            ],
            total: 1,
            page: 1,
            page_size: 50,
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/audit-events$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.auditEvents ?? {
            items: [
              {
                id: 'audit-e2e-request',
                org_id: 'org-e2e',
                route_id: 'route-browser-control',
                actor_user_id: 'employee-risk-owner',
                actor_type: 'user',
                action: 'agent_approval.request',
                status: 'success',
                reason_code: 'requested',
                resource_type: 'agent_approval',
                resource_id: 'approval-e2e-1',
                resource_snapshot: {
                  approval_id: 'approval-e2e-1',
                  action_type: 'browser.remote_control',
                  risk_level: 'high',
                  status: 'pending',
                  route_id: 'route-browser-control',
                },
                metadata: { action_type: 'browser.remote_control' },
                created_at: '2026-05-08T10:01:00Z',
              },
            ],
            total: 1,
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/audit-export$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.auditExport ?? {
            schema_version: 'agent_approval_audit_export.v1',
            generated_at: '2026-05-08T10:05:00Z',
            approval: {
              id: 'approval-e2e-1',
              org_id: 'org-e2e',
              route_id: 'route-browser-control',
              requested_by: 'employee-risk-owner',
              action_type: 'browser.remote_control',
              risk_level: 'high',
              status: 'pending',
              payload: {
                target: 'desktop-runtime',
                reason: '远程执行高风险桌面动作',
              },
              expires_at: '2026-05-08T10:30:00Z',
              created_at: '2026-05-08T10:00:00Z',
              updated_at: '2026-05-08T10:00:00Z',
            },
            audit_events: [
              {
                id: 'audit-e2e-request',
                org_id: 'org-e2e',
                route_id: 'route-browser-control',
                actor_user_id: 'employee-risk-owner',
                actor_type: 'user',
                action: 'agent_approval.request',
                status: 'success',
                reason_code: 'requested',
                resource_type: 'agent_approval',
                resource_id: 'approval-e2e-1',
                resource_snapshot: {
                  approval_id: 'approval-e2e-1',
                  action_type: 'browser.remote_control',
                  risk_level: 'high',
                  status: 'pending',
                  route_id: 'route-browser-control',
                },
                metadata: { action_type: 'browser.remote_control' },
                created_at: '2026-05-08T10:01:00Z',
              },
            ],
            total: 1,
            limit: 500,
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/artifacts\/export$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.workspaceArtifacts?.export ?? {
            schema_version: 'agent_workspace_artifacts_export.v1',
            generated_at: '2026-05-08T10:09:00Z',
            approval: {
              id: 'approval-e2e-1',
              org_id: 'org-e2e',
              route_id: 'route-browser-control',
              requested_by: 'employee-risk-owner',
              action_type: 'browser.remote_control',
              risk_level: 'high',
              status: 'approved',
              payload: {
                target: 'desktop-runtime',
                reason: '远程执行高风险桌面动作',
              },
              expires_at: '2026-05-08T10:30:00Z',
              created_at: '2026-05-08T10:00:00Z',
              updated_at: '2026-05-08T10:05:00Z',
            },
            artifacts: [
              {
                id: 'artifact-e2e-1',
                approval_id: 'approval-e2e-1',
                artifact_type: 'summary',
                title: '高风险工作摘要',
                content: { checkpoint: 'operator-reviewed-workspace' },
                metadata: { source: 'agent-approval-workspace' },
                created_by: 'e2e-admin',
                created_at: '2026-05-08T10:08:00Z',
              },
            ],
            total: 1,
            limit: 100,
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/artifacts$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.workspaceArtifacts?.list ?? {
            items: [],
            total: 0,
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/artifacts$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.workspaceArtifacts?.create ?? {
            allowed: true,
            reason_code: 'artifact_recorded',
            human_message: 'Agent workspace artifact recorded.',
            approval_id: 'approval-e2e-1',
            status: 'approved',
            audit_event_id: 'audit-artifact-e2e-1',
            artifact: {
              id: 'artifact-e2e-1',
              approval_id: 'approval-e2e-1',
              artifact_type: 'summary',
              title: '高风险工作摘要',
              content: { checkpoint: 'operator-reviewed-workspace', status: 'approved' },
              metadata: { source: 'agent-approval-workspace' },
              created_by: 'e2e-admin',
              created_at: '2026-05-08T10:08:00Z',
            },
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/artifacts\/[^/]+$/.test(pathname) && request.method() === 'PATCH') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.workspaceArtifacts?.update ?? {
            allowed: true,
            reason_code: 'artifact_updated',
            human_message: 'Agent workspace artifact updated.',
            approval_id: 'approval-e2e-1',
            status: 'approved',
            audit_event_id: 'audit-artifact-update-e2e-1',
            artifact: {
              id: 'artifact-e2e-1',
              approval_id: 'approval-e2e-1',
              artifact_type: 'summary',
              title: '高风险工作摘要（已复核）',
              content: {
                checkpoint: 'operator-reviewed-workspace',
                status: 'approved',
                review_status: 'human-reviewed',
                reviewed_from: 'agent-approval-workspace',
              },
              metadata: {
                source: 'agent-approval-workspace',
                reviewed_from: 'agent-approval-workspace',
              },
              created_by: 'e2e-admin',
              created_at: '2026-05-08T10:08:00Z',
              updated_by: 'e2e-admin',
              updated_at: '2026-05-08T10:09:00Z',
              revision: 1,
            },
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/approve$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.approve ?? {
            allowed: true,
            reason_code: 'approved',
            human_message: '审批已批准',
            approval_id: 'approval-e2e-1',
            status: 'approved',
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/reject$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.reject ?? {
            allowed: false,
            reason_code: 'rejected',
            human_message: '审批已驳回',
            approval_id: 'approval-e2e-1',
            status: 'rejected',
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/revoke$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.agentApprovals?.revoke ?? {
            allowed: false,
            reason_code: 'revoked',
            human_message: '审批已撤销',
            approval_id: 'approval-e2e-1',
            status: 'revoked',
          },
        ),
      )
    }

    if (/\/agent-approvals\/[^/]+\/workspace-control$/.test(pathname) && request.method() === 'POST') {
      const body = request.postDataJSON() as { action?: string } | null
      if (body?.action === 'observe') {
        return fulfillJson(
          route,
          options.agentApprovals?.workspaceControl ?? buildUnified({
            allowed: true,
            reason_code: 'observe_snapshot_ready',
            human_message: 'Agent workspace observe snapshot prepared.',
            approval_id: 'approval-e2e-1',
            status: 'approved',
            audit_event_id: 'agent-audit-observe-e2e',
            workspace_snapshot: {
              observed_at: '2026-05-09T09:00:00Z',
              observe_audit_event_id: 'agent-audit-observe-e2e',
              approval: {
                approval_id: 'approval-e2e-1',
                action_type: 'browser.remote_control',
                risk_level: 'l4',
                status: 'approved',
                route_id: '',
              },
              artifacts: [
                {
                  id: 'workspace-artifact-e2e-1',
                  approval_id: 'approval-e2e-1',
                  artifact_type: 'summary',
                  title: '高风险工作摘要',
                  content: {
                    action_type: 'browser.remote_control',
                    checkpoint: 'operator-reviewed-workspace',
                  },
                  metadata: { source: 'agent-approval-workspace' },
                  created_by: 'admin-e2e',
                  created_at: '2026-05-09T09:00:00Z',
                },
              ],
              audit_events: [
                {
                  id: 'agent-audit-observe-e2e',
                  org_id: 'org-e2e',
                  actor_user_id: 'admin-e2e',
                  actor_type: 'user',
                  action: 'agent_workspace.observe',
                  status: 'success',
                  reason_code: 'observe_snapshot_ready',
                  resource_type: 'agent_approval',
                  resource_id: 'approval-e2e-1',
                  resource_snapshot: null,
                  metadata: { workspace_control: 'observe' },
                  created_at: '2026-05-09T09:00:00Z',
                },
              ],
              runtime_controls: {
                observe: 'available',
                pause: 'runtime_not_integrated',
                takeover: 'runtime_not_integrated',
                terminate: 'runtime_not_integrated',
              },
            },
          }),
        )
      }
      return fulfillJson(
        route,
        options.agentApprovals?.workspaceControl ?? {
          code: 409,
          data: {
            allowed: false,
            reason_code: 'runtime_not_integrated',
            human_message: 'Agent runtime control is not integrated yet; the control action was rejected fail-closed.',
            approval_id: 'approval-e2e-1',
            status: 'approved',
          },
          message: 'Agent runtime control is not integrated yet; the control action was rejected fail-closed.',
          request_id: 'e2e-request',
        },
      )
    }

    if (pathname.includes('/notifications')) {
      return fulfillJson(route, buildUnified({ data: [], total: 0 }))
    }

    if (pathname.endsWith('/llm/providers') && request.method() === 'GET') {
      return fulfillJson(
        route,
        options.llm?.providers ?? {
          openai: {
            name: 'OpenAI Compatible',
            base_url: 'https://api.example.test/v1',
            models: { llm: ['gpt-4o-mini', 'gpt-4o'], embedding: ['text-embedding-3-small'] },
            supports_streaming: true,
            api_key_required: true,
            is_local: false,
            openai_compatible: true,
          },
          ollama: {
            name: 'Ollama',
            base_url: 'http://localhost:11434/v1',
            models: { llm: ['qwen2.5:7b'] },
            supports_streaming: true,
            api_key_required: false,
            is_local: true,
            openai_compatible: true,
          },
        },
      )
    }

    if (pathname.endsWith('/llm/configs') && request.method() === 'GET') {
      return fulfillJson(route, llmConfigState)
    }

    if (pathname.endsWith('/llm/configs') && request.method() === 'POST') {
      const body = (request.postDataJSON() ?? {}) as Record<string, unknown>
      options.llm?.onCreate?.(body)
      const created = {
        id: 'llm-e2e-created',
        api_key_masked: body.api_key ? 'sk-n...cret' : null,
        is_active: true,
        created_at: '2026-05-09T10:10:00Z',
        updated_at: '2026-05-09T10:10:00Z',
        top_p: 1,
        frequency_penalty: 0,
        presence_penalty: 0,
        context_length: 4096,
        extra_params: {},
        total_calls: 0,
        total_tokens: 0,
        avg_latency: null,
        ...body,
      }
      llmConfigState = {
        ...llmConfigState,
        items: [created, ...(llmConfigState.items ?? [])],
        total: (llmConfigState.total ?? 0) + 1,
      }
      return fulfillJson(route, created)
    }

    if (/\/llm\/configs\/[^/]+$/.test(pathname) && request.method() === 'PUT') {
      const id = pathname.split('/').pop() ?? ''
      const body = (request.postDataJSON() ?? {}) as Record<string, unknown>
      options.llm?.onUpdate?.(body)
      const current = (llmConfigState.items ?? []).find((item) => item.id === id) ?? {}
      const updated = {
        ...current,
        ...body,
        id,
        api_key_masked: body.api_key ? 'sk-r...ment' : current.api_key_masked,
        updated_at: '2026-05-09T10:11:00Z',
      }
      llmConfigState = {
        ...llmConfigState,
        items: (llmConfigState.items ?? []).map((item) => (item.id === id ? updated : item)),
      }
      return fulfillJson(route, updated)
    }

    if (/\/llm\/configs\/[^/]+\/test$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(route, options.llm?.testSavedConfig ?? { success: true, message: 'ok', response_time_ms: 42 })
    }

    if (pathname.endsWith('/llm/test-connection') && request.method() === 'POST') {
      return fulfillJson(route, options.llm?.testConnection ?? { success: true, message: 'ok', response_time_ms: 45 })
    }

    if (/\/llm\/configs\/[^/]+\/set-default$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(route, (llmConfigState.items ?? [])[0] ?? {})
    }

    if (/\/llm\/configs\/[^/]+\/toggle-active$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(route, (llmConfigState.items ?? [])[0] ?? {})
    }

    if (/\/llm\/configs\/[^/]+$/.test(pathname) && request.method() === 'DELETE') {
      return fulfillJson(route, { success: true, message: '配置已删除' })
    }

    if (pathname.endsWith('/chat/history') && request.method() === 'GET') {
      return fulfillJson(route, buildUnified({ conversations: [], messages: [] }))
    }

    if (pathname.includes('/chat/conversations/') && pathname.endsWith('/canvas')) {
      return fulfillJson(route, buildUnified(null))
    }

    if (pathname.includes('/harness/stats')) {
      return fulfillJson(route, {
        status: 'ok',
        data: {
          cost: { total_tokens: 1024, total_cost_usd: 0.12, by_model: {}, by_agent: {} },
          tools: { total: 8, enabled: 8 },
          policy: { total_checks: 12, deny_count: 1 },
          tasks: { total: 5, success: 5, failed: 0 },
        },
      })
    }

    if (/\/harness\/policy\/agent\/[^/]+\/tools$/.test(pathname)) {
      return fulfillJson(route, {
        status: 'ok',
        data: options.harness?.agentTools ?? {
          agent: 'legal_researcher',
          available_tools: ['search_knowledge', 'risk_assessment'],
        },
      })
    }

    if (pathname.includes('/harness/tools')) {
      return fulfillJson(route, {
        status: 'ok',
        data: options.harness?.tools ?? [
          {
            name: 'search_knowledge',
            display_name: '知识库检索',
            description: '检索组织知识库与法规材料',
            risk_level: 'low',
            requires_approval: false,
            tags: ['knowledge'],
          },
          {
            name: 'draft_contract',
            display_name: '合同起草',
            description: '生成或修改合同草稿',
            risk_level: 'medium',
            requires_approval: true,
            tags: ['contract'],
          },
          {
            name: 'risk_assessment',
            display_name: '风险评估',
            description: '评估企业经营风险',
            risk_level: 'high',
            requires_approval: true,
            tags: ['risk'],
          },
        ],
      })
    }

    if (pathname.includes('/harness/policy/check')) {
      return fulfillJson(route, {
        status: 'ok',
        data: { decision: 'deny' },
      })
    }

    if (pathname.endsWith('/sync/remote-control/status') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.remoteControl?.status ?? {
            available: false,
            status: 'not_configured',
            desktop_device_id: null,
            pairing_id: null,
            queued_command_count: 0,
            required_controls: [
              'device_pairing',
              'desktop_confirmation',
              'capability_route_token',
              'command_expiry_and_revocation',
              'audit_log',
            ],
            message: '移动远控桌面尚未创建持久化配对、命令队列和审计闭环；默认不可用。',
          },
        ),
      )
    }

    if (pathname.endsWith('/sync/remote-control/audit-events') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.remoteControl?.auditEvents ?? {
            items: [],
            total: 0,
          },
        ),
      )
    }

    if (pathname.endsWith('/sync/remote-control/route-token') && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.remoteControl?.routeToken ?? {
            allowed: true,
            reason_code: 'route_token_issued',
            human_message: 'ok',
            route_token: 'e2e-route-token',
            route_id: 'route-e2e',
            pairing_id: 'pairing-e2e',
            required_scope: 'desktop:control',
            route_key: 'desktop-control',
            expires_at: '2026-05-09T10:05:00Z',
          },
        ),
      )
    }

    if (/\/sync\/remote-control\/commands\/[^/]+\/cancel$/.test(pathname) && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.remoteControl?.cancelCommand ?? {
            command_id: 'command-e2e',
            pairing_id: 'pairing-e2e',
            desktop_device_id: 'desktop-e2e',
            command_type: 'desktop.status_probe',
            risk_level: 'l2',
            status: 'cancelled',
            route_scopes: ['desktop:control'],
            second_confirmed: false,
            cancelled_at: '2026-05-09T10:04:00Z',
          },
        ),
      )
    }

    if (pathname.endsWith('/mcp/servers') && request.method() === 'GET') {
      return fulfillJson(route, options.mcp?.servers ?? [])
    }

    if (pathname.endsWith('/knowledge-center/graph/overview') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.graph?.overview ?? {
            available: true,
            total_nodes: 0,
            total_edges: 0,
            node_types: {},
            relation_types: {},
          },
        ),
      )
    }

    if (pathname.endsWith('/knowledge-center/graph/search') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(options.graph?.search ?? { nodes: [], edges: [], total: 0 }),
      )
    }

    if (pathname.endsWith('/knowledge-center/graph/types') && request.method() === 'GET') {
      return fulfillJson(route, buildUnified(options.graph?.types ?? []))
    }

    if (/\/knowledge-center\/graph\/entity\/[^/]+\/detail$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(route, buildUnified(options.graph?.detail ?? {}))
    }

    if (/\/knowledge-center\/graph\/subgraph\/[^/]+$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(options.graph?.subgraph ?? { center: 'e2e', nodes: [], edges: [] }),
      )
    }

    if (pathname.endsWith('/knowledge/bases') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.knowledge?.bases ?? { items: [], total: 0, page: 1, page_size: 20 },
        ),
      )
    }

    if (/\/knowledge\/bases\/[^/]+\/documents$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.knowledge?.documents ?? { items: [], total: 0, page: 1, page_size: 50 },
        ),
      )
    }

    if (/\/knowledge\/bases\/[^/]+\/stats$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.knowledge?.stats ?? {
            kb_id: 'kb-e2e',
            name: '默认知识库',
            doc_count: 0,
            processed_count: 0,
            total_chunks: 0,
            categories: {},
          },
        ),
      )
    }

    if (pathname.endsWith('/knowledge/search') && request.method() === 'POST') {
      return fulfillJson(route, buildUnified(options.knowledge?.search ?? []))
    }

    if (pathname.endsWith('/knowledge/rag-query') && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.knowledge?.ragQuery ?? {
            answer: '未找到可用知识库内容。',
            sources: [],
            context_used: false,
          },
        ),
      )
    }

    if (/\/knowledge\/documents\/[^/]+$/.test(pathname) && request.method() === 'GET') {
      return fulfillJson(route, buildUnified(options.knowledge?.document ?? {}))
    }

    if (pathname.endsWith('/contracts/') || pathname.endsWith('/contracts')) {
      if (request.method() === 'GET') {
        return fulfillJson(
          route,
          buildUnified(
            options.contracts?.list ?? { items: [], total: 0, page: 1, page_size: 20 },
          ),
        )
      }

      if (request.method() === 'POST') {
        return fulfillJson(
          route,
          buildUnified(
            options.contracts?.create ?? {
              id: 'contract-e2e',
              title: '待审查合同',
              contract_type: 'other',
              status: 'draft',
              created_at: '2026-04-03T00:00:00Z',
              updated_at: '2026-04-03T00:00:00Z',
            },
          ),
        )
      }
    }

    if (/\/contracts\/[^/]+\/review$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.contracts?.review ?? {
            contract_id: 'contract-e2e',
            risk_level: 'medium',
            risk_score: 0.42,
            summary: '已完成合同审查',
            risks: [],
            suggestions: [],
            key_terms: {},
          },
        ),
      )
    }

    if (pathname.endsWith('/documents/') || pathname.endsWith('/documents')) {
      return fulfillJson(
        route,
        buildUnified(
          options.documents?.list ?? { items: [], total: 0, page: 1, page_size: 20 },
        ),
      )
    }

    if (/\/documents\/[^/]+$/.test(pathname)) {
      const listItems = (options.documents?.list as { items?: unknown[] } | undefined)?.items
      const fallbackDocument = Array.isArray(listItems) && listItems.length > 0 ? listItems[0] : {}
      return fulfillJson(
        route,
        buildUnified(
          options.documents?.get ?? fallbackDocument,
        ),
      )
    }

    if (pathname.endsWith('/collaboration/sessions')) {
      return fulfillJson(
        route,
        buildUnified(
          options.collaboration?.sessions ?? { items: [], total: 0, page: 1, page_size: 20 },
        ),
      )
    }

    if (/\/collaboration\/sessions\/[^/]+\/collaborators$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.collaboration?.collaborators ?? [],
        ),
      )
    }

    if (/\/collaboration\/sessions\/[^/]+\/snapshots$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.collaboration?.snapshots ?? [],
        ),
      )
    }

    if (/\/collaboration\/sessions\/[^/]+\/snapshots\/[^/]+\/restore$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.collaboration?.restore ?? {
            success: true,
            new_version: 2,
            restored_from_version: 1,
          },
        ),
      )
    }

    if (/\/collaboration\/sessions\/[^/]+$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.collaboration?.session ?? {
            id: 'collab-session-e2e',
            document_id: 'document-real-1',
            name: '默认协作会话',
            status: 'active',
            current_version: 1,
            active_collaborators: 2,
            max_collaborators: 10,
            started_at: '2026-04-06T00:00:00Z',
            last_activity_at: '2026-04-06T00:00:00Z',
            created_at: '2026-04-06T00:00:00Z',
          },
        ),
      )
    }

    if (/\/documents\/[^/]+\/analyze$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.documents?.analyze ?? {
            document_id: 'document-e2e',
            summary: '已完成文档分析',
            key_points: [],
            entities: [],
            dates: [],
            amounts: [],
            risks: [],
          },
        ),
      )
    }

    if (pathname.includes('/cases/')) {
      return fulfillJson(
        route,
        buildUnified({ items: [], total: 0, page: 1, page_size: 20 }),
      )
    }

    if (pathname.endsWith('/tasks/') || pathname.endsWith('/tasks')) {
      return fulfillJson(
        route,
        buildUnified(options.tasks?.list ?? { items: [], total: 0 }),
      )
    }

    if (/\/tasks\/[^/]+\/transition$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.tasks?.transition ?? {
            id: 'task-e2e',
            status: 'in_progress',
          },
        ),
      )
    }

    if (pathname.includes('/leads/')) {
      return fulfillJson(route, buildUnified({ items: [], total: 0 }))
    }

    if (pathname.endsWith('/lawyer/consultations') && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.lawyer?.consultation ?? {
            consultation_id: 'consultation-e2e',
            anonymous_summary: '劳动争议匿名摘要',
          },
        ),
      )
    }

    if (pathname.endsWith('/lawyer/lawyers') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.lawyer?.lawyers ?? {
            items: [],
            total: 0,
          },
        ),
      )
    }

    if (/\/lawyer\/consultations\/[^/]+\/delegate$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.lawyer?.delegation ?? {
            id: 'delegation-e2e',
            status: 'submitted',
          },
        ),
      )
    }

    if (pathname.includes('/auth/features')) {
      return fulfillJson(
        route,
        buildUnified({
          email_verify_enabled: false,
          sms_enabled: false,
          oauth_wechat_enabled: false,
          oauth_alipay_enabled: false,
        }),
      )
    }

    return fulfillJson(route, buildUnified({}))
  })
}

export async function seedAuthState(page: Page, seed: AuthSeed) {
  await page.addInitScript((input: AuthSeed) => {
    const encodeBase64Url = (value: string) =>
      btoa(value).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')

    const header = encodeBase64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    const payload = encodeBase64Url(
      JSON.stringify({
        sub: input.userId ?? 'e2e-user',
        role: input.role,
        exp: input.expired
          ? Math.floor(Date.now() / 1000) - 60
          : Math.floor(Date.now() / 1000) + 60 * 60,
      }),
    )
    const token = `${header}.${payload}.signature`
    const user: Record<string, unknown> = {
      id: input.userId ?? 'e2e-user',
      email: input.email ?? `${input.role}@example.com`,
      name: input.name ?? 'E2E User',
      role: input.role,
    }
    if (input.primary_client) {
      user.primary_client = input.primary_client
    }

    localStorage.setItem('access_token', token)
    localStorage.setItem('refresh_token', 'e2e-refresh-token')
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          user,
          token,
          isAuthenticated: true,
        },
        version: 0,
      }),
    )
    localStorage.setItem('user_info', JSON.stringify(user))

    const sockets: Array<{ url: string; emitMessage: (payload: unknown) => void }> = []

    const emitChatPayload = (socket: MockWebSocket, payload: unknown, delay = 50) => {
      window.setTimeout(() => socket.emitMessage(payload), delay)
    }

    class MockWebSocket extends EventTarget {
      static CONNECTING = 0
      static OPEN = 1
      static CLOSING = 2
      static CLOSED = 3

      url: string
      readyState = MockWebSocket.CONNECTING
      onopen: ((event: Event) => void) | null = null
      onmessage: ((event: MessageEvent) => void) | null = null
      onerror: ((event: Event) => void) | null = null
      onclose: ((event: CloseEvent) => void) | null = null

      constructor(url: string) {
        super()
        this.url = url
        sockets.push(this)

        queueMicrotask(() => {
          this.readyState = MockWebSocket.OPEN
          const event = new Event('open')
          this.onopen?.(event)
          this.dispatchEvent(event)
        })
      }

      send(data?: string) {
        if (!data || !this.url.includes('/chat/ws/')) return

        try {
          const parsed = JSON.parse(data) as {
            content?: string
            type?: string
            original_content?: string
          }

          if (parsed.type === 'clarification_response') {
            emitChatPayload(this, {
              type: 'done',
              content: '已收到补充信息，我将根据您的要求继续生成法律文书。',
              agent: '需求分析Agent',
            })
            return
          }

          const content = parsed.content ?? ''

          if (content.includes('帮我起草一份合同')) {
            emitChatPayload(this, {
              type: 'clarification_request',
              message: '请补充合同类型和交易背景，以便我为您准确起草。',
              original_content: content,
              questions: [
                {
                  question: '请选择合同类型',
                  options: ['买卖合同', '租赁合同', '服务合同'],
                },
              ],
            })
            return
          }

          if (content.includes('劳动法规定试用期最长多久')) {
            emitChatPayload(this, {
              type: 'done',
              content: '根据《劳动合同法》，试用期最长不得超过六个月，具体取决于劳动合同期限。',
              agent: '法律咨询Agent',
            })
            return
          }

          if (content.includes('租赁合同模板')) {
            emitChatPayload(this, {
              type: 'done',
              content: '您可以前往法律智库浏览并下载租赁合同模板，也可以告诉我具体场景后为您定制。',
              agent: '模板助手',
            })
            return
          }

          if (content.trim() === '你好') {
            emitChatPayload(this, {
              type: 'done',
              content: '您好！很高兴为您服务，请告诉我您需要处理的法律问题。',
              agent: '安心智能助手',
            })
            return
          }

          emitChatPayload(this, {
            type: 'done',
            content: '已收到您的问题，正在为您整理专业意见。',
            agent: '安心智能助手',
          })
        } catch {
          // Ignore malformed mock payloads to keep tests deterministic.
        }
      }

      close(code = 1000, reason = 'mock close') {
        this.readyState = MockWebSocket.CLOSED
        const event = new CloseEvent('close', { code, reason, wasClean: true })
        this.onclose?.(event)
        this.dispatchEvent(event)
      }

      emitMessage(payload: unknown) {
        const event = new MessageEvent('message', {
          data: JSON.stringify(payload),
        })
        this.onmessage?.(event)
        this.dispatchEvent(event)
      }
    }

    const globalWindow = window as unknown as {
      WebSocket: typeof WebSocket
      __mockSockets?: Array<{ url: string; emitMessage: (payload: unknown) => void }>
    }
    globalWindow.__mockSockets = sockets
    globalWindow.WebSocket = MockWebSocket as unknown as typeof WebSocket
  }, seed)
}

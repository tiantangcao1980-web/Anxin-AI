import { expect, test } from '@playwright/test'

import { loginAsAdmin, loginAsRole } from './helpers/auth'

const agentApprovalFixture = {
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
}

const approvedAgentApprovalFixture = {
  ...agentApprovalFixture,
  items: [
    {
      ...agentApprovalFixture.items[0],
      status: 'approved',
      decided_by: 'e2e-admin',
      resolved_at: '2026-05-08T10:05:00Z',
      updated_at: '2026-05-08T10:05:00Z',
    },
  ],
}

const skillGovernanceFixture = {
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
    {
      id: 'skill-e2e-2',
      org_id: 'org-e2e',
      skill_name: 'tax-risk',
      current_version: '2.0.0',
      proposed_version: '2.1.0',
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
    {
      id: 'skill-e2e-3',
      org_id: 'org-e2e',
      skill_name: 'mcp-browser-use',
      current_version: '0.2.0',
      proposed_version: '0.3.0',
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
  ],
  total: 3,
  page: 1,
  page_size: 20,
}

test.describe('Agent 审批工作台', () => {
  test('桌面端可以进入高风险 Agent 审批并执行批准动作', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop decision workflow coverage only')
    await loginAsAdmin(page, {
      agentApprovals: {
        list: agentApprovalFixture,
        auditEvents: {
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
        auditExport: {
          schema_version: 'agent_approval_audit_export.v1',
          generated_at: '2026-05-08T10:05:00Z',
          approval: agentApprovalFixture.items[0],
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
        pendingCount: { pending: 1 },
      },
    })

    await page.goto('/agent-approvals')

    await expect(page.getByRole('heading', { name: 'Agent 审批工作台' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'AI审批' })).toBeVisible()
    await expect(page.getByText('高风险智能体动作')).toBeVisible()
    await expect(page.getByTestId('agent-approval-row-approval-e2e-1')).toContainText('browser / remote control')
    await expect(page.getByText('待审批').first()).toBeVisible()

    const row = page.getByTestId('agent-approval-row-approval-e2e-1')
    await row.getByRole('button', { name: '审计' }).click()
    await expect(page.getByTestId('agent-approval-audit-trail')).toContainText('agent approval / request')
    await expect(page.getByTestId('agent-approval-audit-trail')).toContainText('success · requested')

    const exportRequest = page.waitForRequest((request) =>
      request.method() === 'GET' && request.url().includes('/agent-approvals/approval-e2e-1/audit-export'),
    )
    await row.getByRole('button', { name: '导出' }).click()
    await exportRequest
    await expect(page.getByText('审计导出已生成', { exact: true })).toBeVisible()

    const approvalRequest = page.waitForRequest((request) =>
      request.method() === 'POST' && request.url().includes('/agent-approvals/approval-e2e-1/approve'),
    )
    await row.getByRole('button', { name: '批准' }).click()
    await approvalRequest

    await expect(page.getByText('审批已批准', { exact: true })).toBeVisible()
  })

  test('桌面端可以治理 Skill 提案、审计和灰度发布', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop skill governance coverage only')
    await loginAsAdmin(page, {
      agentApprovals: {
        list: agentApprovalFixture,
        pendingCount: { pending: 1 },
      },
      skillGovernance: {
        list: skillGovernanceFixture,
        enabled: {
          skill_name: 'contract-review',
          enabled_version: '1.0.0',
          enabled: true,
        },
      },
    })

    await page.goto('/agent-approvals')

    await expect(page.getByTestId('skill-governance-panel')).toContainText('Skills 进化治理')
    await expect(page.getByTestId('skill-governance-panel')).toContainText('contract-review · 启用 1.0.0')
    await expect(page.getByTestId('skill-governance-row-skill-e2e-1')).toContainText('contract-review 1.0.0 → 1.1.0')
    await expect(page.getByTestId('skill-governance-row-skill-e2e-2')).toContainText('已评测')
    await expect(page.getByTestId('skill-governance-row-skill-e2e-3')).toContainText('已批准')
    await expect(page.getByTestId('capability-policy-panel')).toContainText('能力策略')
    await expect(page.getByTestId('capability-policy-panel')).toContainText('legal_researcher · 可用 2 · 阻断 1')
    await expect(page.getByTestId('capability-policy-tool-list')).toContainText('知识库检索')
    await expect(page.getByTestId('capability-policy-tool-list')).toContainText('可申请')
    await expect(page.getByTestId('capability-route-policy-panel')).toContainText('组织能力策略')
    await expect(page.getByTestId('capability-route-policy-list')).toContainText('browser-fill')

    const routePolicyRequest = page.waitForRequest((request) =>
      request.method() === 'PATCH' && request.url().includes('/agent-approvals/capability-routes/browser-fill'),
    )
    await page.getByTestId('capability-route-browser-fill-toggle').click()
    await routePolicyRequest
    await expect(page.getByText('能力路由已禁用', { exact: true })).toBeVisible()
    await expect(page.getByTestId('capability-route-policy-list')).toContainText('禁用')

    const form = page.getByTestId('skill-governance-proposal-form')
    await form.getByLabel('目标版本').fill('1.2.0')
    const createRequest = page.waitForRequest((request) =>
      request.method() === 'POST' && request.url().includes('/skill-governance/proposals'),
    )
    await form.getByRole('button', { name: '创建' }).click()
    await createRequest
    await expect(page.getByText('Skill 提案已创建', { exact: true })).toBeVisible()

    const draftRow = page.getByTestId('skill-governance-row-skill-e2e-1')
    await draftRow.getByRole('button', { name: '审计' }).click()
    await expect(page.getByTestId('skill-governance-audit-trail')).toContainText('skill evolution / proposal / create')
    await expect(page.getByTestId('skill-governance-audit-trail')).toContainText('success · draft_created')

    const exportRequest = page.waitForRequest((request) =>
      request.method() === 'GET' && request.url().includes('/skill-governance/proposals/skill-e2e-1/audit-export'),
    )
    await draftRow.getByRole('button', { name: '导出' }).click()
    await exportRequest
    await expect(page.getByText('Skill 审计导出已生成', { exact: true })).toBeVisible()

    const evalRequest = page.waitForRequest((request) =>
      request.method() === 'POST' && request.url().includes('/skill-governance/proposals/skill-e2e-1/eval'),
    )
    await draftRow.getByRole('button', { name: '评测' }).click()
    await evalRequest
    await expect(page.getByText('评测结果已记录', { exact: true })).toBeVisible()

    const approveRequest = page.waitForRequest((request) =>
      request.method() === 'POST' && request.url().includes('/skill-governance/proposals/skill-e2e-2/approve'),
    )
    await page.getByTestId('skill-governance-row-skill-e2e-2').getByRole('button', { name: '批准' }).click()
    await approveRequest
    await expect(page.getByText('Skill 提案已批准', { exact: true })).toBeVisible()

    const grayRequest = page.waitForRequest((request) =>
      request.method() === 'POST' && request.url().includes('/skill-governance/proposals/skill-e2e-3/gray-release'),
    )
    await page.getByTestId('skill-governance-row-skill-e2e-3').getByRole('button', { name: '灰度' }).click()
    await grayRequest
    await expect(page.getByText('Skill 已灰度启用', { exact: true })).toBeVisible()
  })

  test('桌面端工作室控制在运行时未接入前 fail-closed', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop workspace control coverage only')
    await loginAsAdmin(page, {
      agentApprovals: {
        list: approvedAgentApprovalFixture,
        pendingCount: { pending: 0 },
      },
    })

    await page.goto('/agent-approvals')
    await page.getByRole('button', { name: '已批准' }).click()

    const row = page.getByTestId('agent-approval-row-approval-e2e-1')
    await expect(row).toContainText('已批准')
    const controlRequest = page.waitForRequest((request) =>
      request.method() === 'POST' && request.url().includes('/agent-approvals/approval-e2e-1/workspace-control'),
    )
    await row.getByRole('button', { name: '暂停' }).click()
    await controlRequest
    await expect(page.getByText(/runtime control is not integrated/)).toBeVisible()
  })

  test('普通员工能力中心只展示基础和可申请能力', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop capability visibility coverage only')
    await loginAsRole(page, 'employee', {
      agentApprovals: {
        list: agentApprovalFixture,
        pendingCount: { pending: 1 },
      },
      harness: {
        agentTools: {
          agent: 'legal_researcher',
          available_tools: ['search_knowledge'],
        },
        tools: [
          {
            name: 'search_knowledge',
            display_name: '知识库检索',
            description: '检索授权知识库',
            risk_level: 'low',
            requires_approval: false,
            tags: ['knowledge'],
          },
          {
            name: 'draft_contract',
            display_name: '合同起草申请',
            description: '申请生成合同草稿',
            risk_level: 'medium',
            requires_approval: true,
            tags: ['contract'],
          },
          {
            name: 'mcp_admin',
            display_name: 'MCP 管理',
            description: '管理组织外部 MCP 连接',
            risk_level: 'high',
            requires_approval: false,
            tags: ['mcp', 'admin'],
          },
          {
            name: 'desktop_remote',
            display_name: '桌面远控',
            description: '远程控制桌面客户端',
            risk_level: 'high',
            requires_approval: true,
            tags: ['desktop'],
          },
        ],
      },
    })

    await page.goto('/agent-approvals')

    await expect(page.getByTestId('capability-role-visibility')).toContainText('employee · 基础与申请 · 已隐藏 2')
    await expect(page.getByTestId('capability-policy-tool-list')).toContainText('知识库检索')
    await expect(page.getByTestId('capability-policy-tool-list')).toContainText('合同起草申请')
    await expect(page.getByTestId('capability-policy-tool-list')).toContainText('可申请')
    await expect(page.getByTestId('capability-policy-tool-list')).not.toContainText('MCP 管理')
    await expect(page.getByTestId('capability-policy-tool-list')).not.toContainText('桌面远控')
  })

  test('移动端工作台内容保持在视口内并高亮协作入口', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile', 'mobile viewport coverage only')
    await loginAsAdmin(page, {
      agentApprovals: {
        list: agentApprovalFixture,
        pendingCount: { pending: 1 },
      },
    })

    await page.goto('/agent-approvals')

    await expect(page.getByRole('heading', { name: 'Agent 审批工作台' })).toBeVisible()
    await expect(page.getByRole('button', { name: '协作' })).toHaveClass(/text-primary/)
    await expect(page.getByTestId('skill-governance-panel')).toBeVisible()
    await expect(page.getByTestId('capability-policy-panel')).toBeVisible()
    await expect(page.getByTestId('agent-approval-row-approval-e2e-1')).toBeVisible()

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
})

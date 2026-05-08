import { expect, test } from '@playwright/test'

import { loginAsAdmin } from './helpers/auth'

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

    const approvalRequest = page.waitForRequest((request) =>
      request.method() === 'POST' && request.url().includes('/agent-approvals/approval-e2e-1/approve'),
    )
    await row.getByRole('button', { name: '批准' }).click()
    await approvalRequest

    await expect(page.getByText('审批已批准', { exact: true })).toBeVisible()
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
    await expect(page.getByTestId('agent-approval-row-approval-e2e-1')).toBeVisible()

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
})

import { expect, test, type Page, type Route } from '@playwright/test'
import { installApiMocks, seedAuthState } from './helpers/session'

function unified(data: unknown) {
  return {
    code: 0,
    data,
    message: 'ok',
    request_id: 'contract-lifecycle-e2e',
  }
}

async function fulfillJson(route: Route, data: unknown) {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(data),
  })
}

async function seedContractLifecycle(page: Page) {
  let versions = [
    {
      id: 'version-1',
      version: 1,
      source: 'baseline',
      description: 'contract review source',
      created_at: '2026-05-06T00:00:00Z',
      created_by: 'e2e-admin',
    },
  ]

  await installApiMocks(page, {
    contracts: {
      list: { items: [], total: 0, page: 1, page_size: 20 },
    },
  })

  await page.route('**/api/v1/contracts/parse', async (route) => {
    await fulfillJson(route, {
      success: true,
      text: '第一条 付款期限为30天。\n\n第二条 违约金为合同金额5%。',
      char_count: 34,
      word_count: 2,
      contract_type: 'service',
      key_info: {},
      structure: {},
    })
  })

  await page.route('**/api/v1/contracts/upload-and-review', async (route) => {
    await fulfillJson(route, {
      contract_id: 'contract-version-e2e',
      contract_number: 'CONTRACT-E2E',
      title: '版本验收合同',
      contract_type: 'service',
      parse_result: {
        char_count: 34,
        word_count: 2,
        key_info: {},
      },
      review_result: {
        contract_id: 'contract-version-e2e',
        risk_score: 0.55,
        risk_level: 'medium',
        summary: '付款周期偏长，建议调整。',
        risks: [
          {
            id: 'risk-payment',
            type: 'payment',
            title: '付款周期过长',
            level: 'high',
            description: '付款期限超过建议值。',
            suggestion: '缩短回款周期',
            original_text: '付款期限为30天',
            suggested_text: '付款期限为10天',
          },
        ],
        suggestions: ['缩短回款周期'],
        key_terms: {},
        missing_clauses: [],
      },
    })
  })

  await page.route('**/api/v1/contracts/contract-version-e2e/versions', async (route) => {
    await fulfillJson(route, unified({ contract_id: 'contract-version-e2e', versions }))
  })

  await page.route('**/api/v1/contracts/contract-version-e2e/apply-suggestions', async (route) => {
    versions = [
      {
        id: 'version-2',
        version: 2,
        source: 'suggestion',
        description: 'accepted risk suggestions',
        created_at: '2026-05-06T00:05:00Z',
        created_by: 'e2e-admin',
      },
      versions[0],
    ]
    await fulfillJson(route, unified({
      modified_text: '第一条 付款期限为10天。\n\n第二条 违约金为合同金额5%。',
    }))
  })

  await page.route('**/api/v1/contracts/contract-version-e2e/versions/diff**', async (route) => {
    await fulfillJson(route, unified({
      contract_id: 'contract-version-e2e',
      from_version: 1,
      to_version: 2,
      summary: { changes: 1, insertions: 0, deletions: 0, replacements: 1 },
      changes: [
        {
          type: 'replace',
          old_start: 1,
          old_end: 1,
          new_start: 1,
          new_end: 1,
          old_text: '第一条 付款期限为30天。',
          new_text: '第一条 付款期限为10天。',
        },
      ],
    }))
  })

  await page.route('**/api/v1/contracts/contract-version-e2e/versions/1/rollback', async (route) => {
    versions = [
      {
        id: 'version-3',
        version: 3,
        source: 'rollback',
        description: 'rollback to version 1',
        created_at: '2026-05-06T00:10:00Z',
        created_by: 'e2e-admin',
      },
      ...versions,
    ]
    await fulfillJson(route, unified({
      contract_id: 'contract-version-e2e',
      status: 'draft',
      version: 3,
      text: '第一条 付款期限为30天。\n\n第二条 违约金为合同金额5%。',
    }))
  })
}

test.describe('TASK-05 contract lifecycle stories', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'Contract lifecycle story uses the desktop review workspace.')
    await seedContractLifecycle(page)
    await seedAuthState(page, {
      role: 'admin',
      userId: 'e2e-admin',
      name: 'E2E Admin',
      email: 'admin@example.com',
    })
  })

  test('reviews, diffs, and rolls back contract versions', async ({ page }) => {
    await page.goto('/management?tab=contracts')
    await page.getByRole('button', { name: '完整审查' }).click()
    await page.locator('input[type="file"]').setInputFiles({
      name: 'contract-version.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('第一条 付款期限为30天。\n\n第二条 违约金为合同金额5%。'),
    })

    await expect(page.getByText('付款周期过长')).toBeVisible()
    await expect(page.getByText('版本时间线')).toBeVisible()
    await expect(page.getByText('v1')).toBeVisible()

    await page.getByRole('button', { name: /一键接受全部/ }).click()
    await page.getByRole('button', { name: /应用修改/ }).click()
    await page.getByRole('button', { name: '返回审阅' }).click()

    await page.getByText('版本时间线').scrollIntoViewIfNeeded()
    await expect(page.getByText('v2')).toBeVisible()
    await page.getByTitle('对比上一版').click()
    await expect(page.getByText('第一条 付款期限为30天。', { exact: true })).toBeVisible()
    await expect(page.getByText('第一条 付款期限为10天。', { exact: true })).toBeVisible()

    page.once('dialog', (dialog) => dialog.accept())
    await page.getByTitle('回滚到此版本').click()

    await expect(page.getByText('v3')).toBeVisible()
    await expect(page.getByText('第一条 付款期限为30天。', { exact: true })).toBeVisible()
  })
})

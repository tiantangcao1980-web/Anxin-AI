import { expect, test } from '@playwright/test'

import { installApiMocks, seedAuthState } from './helpers/session'

test.describe('核心业务动作回归', () => {
  test('企业用户可以完成找律师到确认委托流程', async ({ page }) => {
    await installApiMocks(page, {
      lawyer: {
        consultation: {
          consultation_id: 'consultation-e2e',
          anonymous_summary: '员工主张未签劳动合同双倍工资，拟寻求劳动争议律师协助。',
        },
        lawyers: {
          items: [
            {
              id: 'lawyer-1',
              real_name: '张律师',
              specializations: ['劳动争议'],
              years_of_practice: 9,
              total_cases: 128,
              rating: 4.9,
              law_firm: '安心律师事务所',
              is_online: true,
              is_verified: true,
            },
          ],
          total: 1,
        },
        delegation: {
          id: 'delegation-1',
          status: 'submitted',
        },
      },
    })
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })

    await page.goto('/find-lawyer')
    await page.getByRole('textbox').fill('员工主张公司未签劳动合同并要求赔偿，我们需要尽快处理劳动争议。')
    await page.getByRole('button', { name: '开始匹配律师' }).click()

    await expect(page.getByText('AI 匿名摘要（律师将看到）：')).toBeVisible()
    await expect(page.getByText('张律师')).toBeVisible()

    await page.getByText('张律师').click()
    await page.getByRole('button', { name: '一键委托' }).click()

    await expect(page.getByRole('heading', { name: '确认委托' })).toBeVisible()
    await page.getByRole('button', { name: '确认委托' }).click()

    await expect(page.getByRole('heading', { name: '找律师' })).toBeVisible()
    await expect(page.getByRole('button', { name: '开始匹配律师' })).toBeVisible()
  })

  test('任务中心可以推进任务状态', async ({ page }) => {
    await installApiMocks(page, {
      tasks: {
        list: {
          items: [
            {
              id: 'task-1',
              title: '审查供应商合同',
              description: '补充付款条款与违约责任条款',
              status: 'todo',
              priority: 'high',
              dueDate: '2026-04-10',
              assignee: '张律师',
              caseTitle: '供应商采购案',
              tags: [],
            },
          ],
          total: 1,
        },
        transition: {
          id: 'task-1',
          status: 'in_progress',
        },
      },
    })
    await seedAuthState(page, {
      role: 'admin',
      name: 'Admin User',
      email: 'admin@example.com',
    })

    await page.goto('/tasks')
    await expect(page.getByText('审查供应商合同')).toBeVisible()

    await page.getByRole('button', { name: '开始处理' }).click()

    await expect(page.getByText('进行中', { exact: true }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: '标记完成' })).toBeVisible()
  })

  test('合同管理可以触发智能审查并展示结果', async ({ page }) => {
    await installApiMocks(page, {
      contracts: {
        list: {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        },
        create: {
          id: 'contract-1',
          title: '待审查合同',
          contract_type: 'other',
          status: 'draft',
          created_at: '2026-04-03T00:00:00Z',
          updated_at: '2026-04-03T00:00:00Z',
        },
        review: {
          contract_id: 'contract-1',
          risk_level: 'high',
          risk_score: 0.78,
          summary: '付款条件与违约责任条款存在明显风险。',
          risks: [
            {
              type: 'payment',
              title: '付款条款不明确',
              level: 'high',
              description: '未约定付款节点与逾期责任。',
              suggestion: '补充分期付款与逾期违约金。',
            },
          ],
          suggestions: ['补充付款节点'],
          key_terms: {
            amount: '100万元',
          },
        },
      },
    })
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })

    await page.goto('/contracts')
    await page.getByRole('button', { name: '上传审查' }).click()

    await page.getByPlaceholder('请在此粘贴合同文本...').fill('甲方应在合同生效后付款，违约责任另行协商。')
    await page.getByRole('button', { name: '开始审查' }).click()

    await expect(page.getByText('付款条件与违约责任条款存在明显风险。')).toBeVisible()
    await expect(page.getByText('付款条款不明确')).toBeVisible()
    await expect(page.getByText('风险点 (1)')).toBeVisible()
    await expect(page.getByText('78%')).toBeVisible()
  })

  test('文档库可以触发 AI 分析', async ({ page }) => {
    await installApiMocks(page, {
      documents: {
        list: {
          items: [
            {
              id: 'document-1',
              name: '采购合同草稿.md',
              doc_type: 'contract',
              description: '待分析文档',
              file_size: 2048,
              mime_type: 'text/markdown',
              version: 1,
              ai_summary: null,
              extracted_text: '# 采购合同',
              tags: ['合同'],
              created_at: '2026-04-03T00:00:00Z',
              updated_at: '2026-04-03T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        },
        analyze: {
          document_id: 'document-1',
          summary: '该文档主要涉及付款、交付和违约责任安排。',
          key_points: ['付款条款', '交付条款'],
          entities: ['甲方', '乙方'],
          dates: ['2026-04-03'],
          amounts: ['100万元'],
          risks: ['违约责任需要补强'],
        },
      },
    })
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })

    await page.goto('/documents')
    await page.getByRole('button', { name: '我的文档' }).click()
    await expect(page.getByRole('heading', { name: '我的文档' })).toBeVisible()
    await expect(page.getByText('采购合同草稿.md')).toBeVisible()

    await page.getByTitle('AI分析').click()

    await expect(page.getByText('文档分析完成')).toBeVisible()
  })
})

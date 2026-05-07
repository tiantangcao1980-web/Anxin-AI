import { expect, test, type TestInfo } from '@playwright/test'

import { installApiMocks, seedAuthState } from './helpers/session'

test.describe('RAG 引用来源回链', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await installApiMocks(page, {
      knowledge: {
        bases: {
          items: [
            {
              id: 'kb-laws',
              name: '法规库',
              knowledge_type: 'law',
              doc_count: 1,
              is_public: true,
              created_at: '2026-05-06T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        },
        ragQuery: {
          answer: '根据《民法典》第490条，书面合同通常在各方签名、盖章或者按指印时成立。',
          context_used: true,
          chunks_used: 1,
          sources: [
            {
              id: 'civil_code_490_0',
              doc_id: 'civil_code_490',
              chunk_id: 'civil_code_490_0',
              title: '《民法典》第490条 合同成立时间',
              source: '法规库',
              score: 0.97,
              anchor_text: '采用书面形式订立合同',
              content_snippet: '当事人采用书面形式订立合同的，自当事人均签名、盖章或者按指印时合同成立。',
            },
          ],
        },
        document: {
          id: 'civil_code_490',
          title: '《民法典》第490条 合同成立时间',
          source: '法规库',
          is_processed: true,
          created_at: '2026-05-06T00:00:00Z',
          content: '当事人采用书面形式订立合同的，自当事人均签名、盖章或者按指印时合同成立。',
        },
      },
    })
  })

  test('用户可以从 RAG 回答打开来源并看到命中片段高亮', async ({ page }) => {
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })

    await page.goto('/knowledge-base')
    await page.getByRole('button', { name: '智慧搜索' }).click()
    await page.getByRole('button', { name: 'RAG问答' }).click()
    await page.getByPlaceholder('输入法律问题，AI将结合知识库为您解答...').fill('书面合同什么时候成立？')
    await page.getByRole('button', { name: 'RAG问答' }).last().click()

    await expect(page.getByText('根据《民法典》第490条')).toBeVisible()
    await page.getByRole('button', { name: '《民法典》第490条 合同成立时间' }).click()

    await expect(page.getByText('chunk: civil_code_490_0')).toBeVisible()
    await expect(page.locator('mark', { hasText: '采用书面形式订立合同' })).toBeVisible()
    await expect(page.getByText('相关度')).toBeVisible()
  })
})

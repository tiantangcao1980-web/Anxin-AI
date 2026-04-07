import { test, expect } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'

test.describe('导航结构', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile navigation has dedicated coverage in mobile.spec.ts')
    await loginAsAdmin(page)
  })

  test('documents 路由进入统一文档工作台', async ({ page }) => {
    await page.goto('/documents')

    await expect(page.getByTestId('document-workbench-shell')).toBeVisible()
    await expect(page.getByTestId('document-workbench-topbar')).toBeVisible()
    await expect(page.getByTestId('document-workbench-sidebar')).toBeVisible()
    await expect(page.getByTestId('document-workbench-canvas')).toBeVisible()
    await expect(page.getByTestId('document-workbench-statusbar')).toBeVisible()
  })

  test('collaboration 路由携带协作入口语义进入统一工作台', async ({ page }) => {
    await page.goto('/collaboration/session-123')

    await expect(page).toHaveURL(/\/documents/)
    await expect(page.getByTestId('document-workbench-shell')).toHaveAttribute('data-entry-mode', 'collaboration')
    await expect(page.getByTestId('document-workbench-shell')).toHaveAttribute('data-session-id', 'session-123')
  })

  test('统一工作台支持文档空间和多标签', async ({ page }) => {
    await page.goto('/documents')

    await expect(page.getByRole('button', { name: '最近打开' })).toBeVisible()
    await expect(page.getByRole('button', { name: '我的文档' })).toBeVisible()

    await page.getByRole('button', { name: '打开示例文档' }).click()
    await expect(page.getByTestId('document-tab-example-doc')).toBeVisible()
  })

  test('统一工作台按格式切换画布适配器', async ({ page }) => {
    await page.goto('/documents')

    await page.getByRole('button', { name: '打开 Markdown 示例' }).click()
    await expect(page.getByTestId('markdown-text-adapter')).toBeVisible()

    await page.getByRole('button', { name: '打开 PDF 示例' }).click()
    await expect(page.getByTestId('pdf-preview-adapter')).toBeVisible()
  })

  test('统一工作台支持 Excel 与 PPT 轻量适配入口', async ({ page }) => {
    await page.route('**/documents/?page=1&page_size=8', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'sheet-1',
              name: '项目台账.xlsx',
              doc_type: 'xlsx',
              file_size: 1024,
              version: 1,
              extracted_text: '事项,负责人,状态',
              created_at: '2026-04-06T00:00:00Z',
              updated_at: '2026-04-06T00:00:00Z',
            },
            {
              id: 'deck-1',
              name: '签约汇报.pptx',
              doc_type: 'pptx',
              file_size: 2048,
              version: 1,
              extracted_text: '项目概览',
              created_at: '2026-04-06T00:00:00Z',
              updated_at: '2026-04-06T00:00:00Z',
            },
          ],
          total: 2,
          page: 1,
          page_size: 8,
        }),
      })
    })

    await page.goto('/documents')

    await page.getByRole('button', { name: '项目台账.xlsx' }).click()
    await expect(page.getByTestId('spreadsheet-adapter')).toBeVisible()
    await expect(page.getByTestId('workbench-mode-label')).toContainText('表格')

    await page.getByRole('button', { name: '签约汇报.pptx' }).click()
    await expect(page.getByTestId('presentation-adapter')).toBeVisible()
    await expect(page.getByTestId('workbench-mode-label')).toContainText('演示')
  })

  test('统一工作台会渲染真实 Excel 与 PPT 文档内容', async ({ page }) => {
    await page.route('**/documents/?page=1&page_size=8', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'sheet-real-1',
              name: '回款计划.xlsx',
              doc_type: 'xlsx',
              file_size: 1024,
              version: 1,
              extracted_text: '阶段,负责人,状态\\n首付款,王律师,完成\\n尾款,李法务,待跟进',
              created_at: '2026-04-06T00:00:00Z',
              updated_at: '2026-04-06T00:00:00Z',
            },
            {
              id: 'deck-real-1',
              name: '签约方案汇报.pptx',
              doc_type: 'pptx',
              file_size: 2048,
              version: 1,
              extracted_text: '封面页\\n项目背景\\n关键风险与建议',
              created_at: '2026-04-06T00:00:00Z',
              updated_at: '2026-04-06T00:00:00Z',
            },
          ],
          total: 2,
          page: 1,
          page_size: 8,
        }),
      })
    })

    await page.route('**/documents/sheet-real-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'sheet-real-1',
          name: '回款计划.xlsx',
          doc_type: 'xlsx',
          file_size: 1024,
          version: 1,
          extracted_text: '阶段,负责人,状态\\n首付款,王律师,完成\\n尾款,李法务,待跟进',
          created_at: '2026-04-06T00:00:00Z',
          updated_at: '2026-04-06T00:00:00Z',
        }),
      })
    })

    await page.route('**/documents/deck-real-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'deck-real-1',
          name: '签约方案汇报.pptx',
          doc_type: 'pptx',
          file_size: 2048,
          version: 1,
          extracted_text: '封面页\\n项目背景\\n关键风险与建议',
          created_at: '2026-04-06T00:00:00Z',
          updated_at: '2026-04-06T00:00:00Z',
        }),
      })
    })

    await page.goto('/documents')

    await page.getByRole('button', { name: '回款计划.xlsx' }).click()
    await expect(page.getByTestId('spreadsheet-adapter')).toContainText('首付款')
    await expect(page.getByTestId('spreadsheet-adapter')).toContainText('尾款')

    await page.getByRole('button', { name: '签约方案汇报.pptx' }).click()
    await expect(page.getByTestId('presentation-adapter')).toContainText('项目背景')
    await expect(page.getByTestId('presentation-adapter')).toContainText('关键风险与建议')
  })

  test('documents 归属智能协作模块且在线协作为模板入口', async ({ page }) => {
    await page.goto('/documents')

    await expect(page.getByText('智能协作').first()).toBeVisible()
    await expect(page.getByTestId('document-workbench-shell')).toHaveAttribute('data-entry-mode', 'library')
    await expect(page.getByRole('button', { name: '文档工作台' })).toBeVisible()
    await expect(page.getByRole('button', { name: '协作模板' })).toBeVisible()
    await expect(page.getByRole('button', { name: '最近打开' })).toBeVisible()
    await expect(page.getByRole('button', { name: '我的文档' })).toBeVisible()
  })

  test('统一工作台可打开真实文档列表中的文档', async ({ page }) => {
    await page.route('**/documents/?page=1&page_size=8', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'doc-real-1',
              name: '股权协议审阅稿',
              doc_type: 'contract',
              file_size: 1024,
              version: 1,
              extracted_text: '第一条 股权转让安排',
              created_at: '2026-04-05T10:00:00Z',
              updated_at: '2026-04-05T10:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          page_size: 8,
        }),
      })
    })

    await page.route('**/documents/doc-real-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'doc-real-1',
          name: '股权协议审阅稿',
          doc_type: 'contract',
          file_size: 1024,
          version: 1,
          extracted_text: '第一条 股权转让安排\n第二条 付款节点',
          created_at: '2026-04-05T10:00:00Z',
          updated_at: '2026-04-05T10:00:00Z',
        }),
      })
    })

    await page.goto('/documents')

    await expect(page.getByRole('button', { name: '股权协议审阅稿' })).toBeVisible()
    await page.getByRole('button', { name: '股权协议审阅稿' }).click()
    await expect(page.getByText('第二条 付款节点').first()).toBeVisible()
  })

  test('统一工作台可按关键词过滤真实文档列表', async ({ page }) => {
    await page.route('**/documents/?page=1&page_size=8', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'doc-filter-1',
              name: '股权协议审阅稿',
              doc_type: 'contract',
              file_size: 1024,
              version: 1,
              extracted_text: '第一条 股权转让安排',
              created_at: '2026-04-05T10:00:00Z',
              updated_at: '2026-04-05T10:00:00Z',
            },
            {
              id: 'doc-filter-2',
              name: '劳动合同模板',
              doc_type: 'markdown',
              file_size: 512,
              version: 2,
              extracted_text: '# 劳动合同模板',
              created_at: '2026-04-05T10:00:00Z',
              updated_at: '2026-04-05T10:00:00Z',
            },
          ],
          total: 2,
          page: 1,
          page_size: 8,
        }),
      })
    })

    await page.goto('/documents')

    await page.getByPlaceholder('搜索真实文档').fill('劳动')
    await expect(page.getByRole('button', { name: '劳动合同模板' })).toBeVisible()
    await expect(page.getByRole('button', { name: '股权协议审阅稿' })).toHaveCount(0)
  })

  test('统一工作台支持最近打开视图', async ({ page }) => {
    await page.goto('/documents')

    // 依次打开示例文档，等待每个文档的标签页出现
    await page.getByRole('button', { name: '打开 Markdown 示例' }).click()
    await expect(page.getByRole('button', { name: 'Markdown 示例', exact: true })).toBeVisible()
    await page.getByRole('button', { name: '打开 PDF 示例' }).click()
    await expect(page.getByRole('button', { name: 'PDF 示例文件', exact: true })).toBeVisible()

    // 切换到"最近打开"视图，等待列表出现
    await page.getByTestId('document-workbench-sidebar').getByRole('button', { name: '最近打开' }).click()
    const recentList = page.getByTestId('workbench-recent-list')
    await expect(recentList).toBeVisible({ timeout: 10000 })
    await expect(recentList).toContainText('PDF 示例文件')
    await expect(recentList).toContainText('Markdown 示例')
  })

  test('统一工作台会持久化最近打开记录', async ({ page }) => {
    await page.goto('/documents')

    await page.getByRole('button', { name: '打开 Markdown 示例' }).click()
    await expect(page.getByRole('button', { name: 'Markdown 示例', exact: true })).toBeVisible()

    await page.reload()
    await page.getByTestId('document-workbench-sidebar').getByRole('button', { name: '最近打开' }).click()

    const recentList = page.getByTestId('workbench-recent-list')
    await expect(recentList).toBeVisible()
    await expect(recentList).toContainText('Markdown 示例')
  })

  test('顶部导航栏显示四大业务域', async ({ page }) => {
    const header = page.getByRole('banner')
    await expect(header.getByRole('button', { name: 'AI法务' })).toBeVisible()
    await expect(header.getByRole('button', { name: '智能协作' })).toBeVisible()
    await expect(header.getByRole('button', { name: '智能调查' })).toBeVisible()
    await expect(header.getByRole('button', { name: '法律智库' })).toBeVisible()
  })

  test('点击智能协作显示侧边栏', async ({ page }) => {
    await page.getByRole('banner').getByRole('button', { name: '智能协作' }).click()
    await page.waitForURL(/\/cases/)
    await expect(page.getByRole('main').getByRole('heading', { name: '案件管理' })).toBeVisible()
  })

  test('案件管理页面加载', async ({ page }) => {
    await page.goto('/cases')
    await expect(page.getByRole('main').getByRole('heading', { name: '案件管理' })).toBeVisible()
    await expect(page.getByRole('button', { name: '新建案件' })).toBeVisible()
  })

  test('合同管理页面加载', async ({ page }) => {
    await page.goto('/contracts')
    await expect(page.getByText('合同审查').first()).toBeVisible()
  })
})

import { expect, test, type Page } from '@playwright/test'
import { installApiMocks, seedAuthState } from './helpers/session'

const taskDocument = {
  id: 'task-06-document',
  name: 'TASK-06 对象存储验收.md',
  doc_type: 'markdown',
  mime_type: 'text/markdown',
  file_size: 128,
  version: 1,
  extracted_text: '# TASK-06 对象存储验收\n\n上传、导出、协作链路验收内容。',
  created_at: '2026-05-06T00:00:00Z',
  updated_at: '2026-05-06T00:00:00Z',
}

const collaborationSession = {
  id: 'task-06-collaboration',
  document_id: taskDocument.id,
  name: 'TASK-06 双人协作会话',
  status: 'active',
  current_version: 12,
  active_collaborators: 2,
  max_collaborators: 10,
  started_at: '2026-05-06T00:00:00Z',
  last_activity_at: '2026-05-06T01:00:00Z',
  created_at: '2026-05-06T00:00:00Z',
}

const collaborators = [
  {
    id: 'collaborator-owner',
    user_id: 'e2e-owner',
    nickname: '张律师',
    role: 'owner',
    is_online: true,
    last_seen_at: '2026-05-06T01:00:00Z',
  },
  {
    id: 'collaborator-reviewer',
    user_id: 'e2e-reviewer',
    nickname: '李法务',
    role: 'commenter',
    is_online: true,
    last_seen_at: '2026-05-06T01:00:00Z',
  },
]

async function seedDocumentUser(page: Page, userId = 'e2e-admin') {
  await installApiMocks(page, {
    documents: {
      list: { items: [taskDocument], total: 1, page: 1, page_size: 20 },
      get: taskDocument,
    },
    collaboration: {
      session: collaborationSession,
      collaborators,
      snapshots: [
        {
          id: 'snapshot-task-06',
          version: 12,
          created_at: '2026-05-06T01:00:00Z',
          snapshot_type: 'manual',
          description: 'TASK-06 验收快照',
        },
      ],
    },
  })
  await seedAuthState(page, {
    role: 'admin',
    userId,
    name: userId === 'e2e-reviewer' ? '李法务' : '张律师',
    email: `${userId}@example.com`,
  })
}

async function mockDocumentUpload(page: Page) {
  let uploadBody = ''
  await page.route('**/api/v1/documents/', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback()
      return
    }
    uploadBody = route.request().postData() ?? ''
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...taskDocument,
        id: 'task-06-uploaded',
        name: '上传验收.md',
        extracted_text: '# 上传验收\n\n文件已经进入文档工作台。',
      }),
    })
  })
  return () => uploadBody
}

test.describe('TASK-06 document delivery stories', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'Document workbench delivery stories use the desktop workbench.')
    await seedDocumentUser(page)
  })

  test('uploads a document and opens it in the workbench', async ({ page }) => {
    const getUploadBody = await mockDocumentUpload(page)

    await page.goto('/documents')
    await page.locator('input[type="file"]').setInputFiles({
      name: 'upload-acceptance.md',
      mimeType: 'text/markdown',
      buffer: Buffer.from('# 上传验收\n\n文件已经进入文档工作台。'),
    })

    await expect(page.getByTestId('workbench-active-title')).toContainText('上传验收.md')
    await expect(page.getByTestId('markdown-text-adapter')).toContainText('文件已经进入文档工作台')
    expect(getUploadBody()).toContain('upload-acceptance.md')
  })

  test('downloads the active document with matching markdown content', async ({ page }) => {
    await page.goto('/documents')
    await page.getByRole('button', { name: taskDocument.name }).click()
    await expect(page.getByTestId('markdown-text-adapter')).toContainText('上传、导出、协作链路验收内容。')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出' }).click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toBe(`${taskDocument.name}.md`)
    const downloadPath = await download.path()
    expect(downloadPath).toBeTruthy()
    const content = await download.createReadStream().then(
      (stream) =>
        new Promise<string>((resolve, reject) => {
          const chunks: Buffer[] = []
          stream.on('data', (chunk) => chunks.push(Buffer.from(chunk)))
          stream.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')))
          stream.on('error', reject)
        }),
    )
    expect(content).toContain('上传、导出、协作链路验收内容。')
  })

  test('opens the same collaboration session for two users', async ({ browser }) => {
    const ownerContext = await browser.newContext()
    const reviewerContext = await browser.newContext()
    const ownerPage = await ownerContext.newPage()
    const reviewerPage = await reviewerContext.newPage()

    try {
      await seedDocumentUser(ownerPage, 'e2e-owner')
      await seedDocumentUser(reviewerPage, 'e2e-reviewer')

      await Promise.all([
        ownerPage.goto('/collaboration/task-06-collaboration'),
        reviewerPage.goto('/collaboration/task-06-collaboration'),
      ])

      for (const page of [ownerPage, reviewerPage]) {
        await expect(page).toHaveURL(/\/documents/)
        await expect(page.getByTestId('document-workbench-shell')).toHaveAttribute('data-entry-mode', 'collaboration')
        await expect(page.getByTestId('document-workbench-shell')).toHaveAttribute('data-session-id', 'task-06-collaboration')
        await expect(page.getByRole('tab', { name: '协作' })).toHaveAttribute('data-state', 'active')
        await expect(page.getByText('TASK-06 双人协作会话')).toBeVisible()
        await expect(page.getByText('版本 12')).toBeVisible()
        await expect(page.getByText('在线 2/10')).toBeVisible()
        await expect(page.getByText('张律师')).toBeVisible()
        await expect(page.getByText('李法务')).toBeVisible()
      }
    } finally {
      await ownerContext.close()
      await reviewerContext.close()
    }
  })
})


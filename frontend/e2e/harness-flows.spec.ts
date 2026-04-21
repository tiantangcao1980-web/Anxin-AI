/**
 * Harness Engineering 核心流程 E2E 测试
 *
 * 覆盖 Phase 1-3 的关键行为变化：
 * 1. 多轮追问：信息不足不放行
 * 2. 模板请求：返回下载卡片不走AI生成
 * 3. 专业模式：跳过引导直达Agent
 * 4. Harness 监控面板
 */

import { test, expect } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'
import { installApiMocks } from './helpers/session'

test.describe('需求挖掘严格化', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('模糊请求触发追问而非直接生成', async ({ page }) => {
    // 输入模糊的合同起草请求
    const input = page.getByPlaceholder(/发送消息或输入/)
    await input.fill('帮我起草一份合同')
    await input.press('Enter')

    // 应该出现追问（ClarificationBubble），而非直接生成合同
    // 等待后端响应（可能是追问或思考状态）
    await expect(
      page.getByText(/请补充|需求确认|合同类型|请选择/).first()
    ).toBeVisible({ timeout: 30000 })

    // 不应该直接出现合同正文
    const contractContent = page.locator('text=甲方（出卖人）')
    await expect(contractContent).not.toBeVisible({ timeout: 3000 })
  })

  test('法律咨询类问题直接回答（低门槛）', async ({ page }) => {
    const input = page.getByPlaceholder(/发送消息或输入/)
    await input.fill('劳动法规定试用期最长多久？')
    await input.press('Enter')

    // 法律咨询问题应该直接回答，不需要追问
    await expect(
      page.locator('.prose, [class*="ai"], [class*="assistant"]').first()
    ).toBeVisible({ timeout: 30000 })
  })
})

test.describe('模板请求识别', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('模板请求返回下载引导而非AI生成', async ({ page }) => {
    const input = page.getByPlaceholder(/发送消息或输入/)
    await input.fill('给我一个租赁合同模板')
    await input.press('Enter')

    // 应该出现模板相关的回复（包含"模板"、"下载"、"法律智库"等关键词）
    await expect(
      page.locator('.prose, [class*="ai"], [class*="assistant"]')
        .filter({ hasText: /模板|下载|法律智库|浏览/ })
        .first()
    ).toBeVisible({ timeout: 30000 })
  })
})

test.describe('快捷操作栏', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('输入编排栏固定为知识库在左更多在右且无模板主入口', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile has a compact layout')

    const bar = page.getByTestId('input-orchestration-bar')
    const knowledgeButton = bar.getByTestId('knowledge-base-trigger')
    const consultButton = bar.getByRole('button', { name: '快速咨询' })
    const moreButton = bar.getByRole('button', { name: '更多' })

    await expect(knowledgeButton).toBeVisible()
    await expect(consultButton).toBeVisible()
    await expect(bar.getByRole('button', { name: '合同审查' })).toBeVisible()
    await expect(bar.getByRole('button', { name: '文书起草' })).toBeVisible()
    await expect(moreButton).toBeVisible()
    await expect(bar.getByRole('button', { name: '模板' })).not.toBeVisible()

    const [knowledgeBox, consultBox, moreBox] = await Promise.all([
      knowledgeButton.boundingBox(),
      consultButton.boundingBox(),
      moreButton.boundingBox(),
    ])

    expect(knowledgeBox).not.toBeNull()
    expect(consultBox).not.toBeNull()
    expect(moreBox).not.toBeNull()

    expect(knowledgeBox!.x).toBeLessThan(consultBox!.x)
    expect(moreBox!.x).toBeGreaterThan(consultBox!.x)
  })

  test('知识库入口升级为资源选择器并包含模板视图', async ({ page }) => {
    const trigger = page.getByTestId('knowledge-base-trigger')
    await trigger.click()

    await expect(page.getByRole('tab', { name: '全部' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '知识库' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '模板' })).toBeVisible()

    await page.getByRole('tab', { name: '模板' }).click()
    await expect(page.getByText('法律意见书', { exact: true })).toBeVisible()
  })

  test('选择模板后知识库触发器显示模板上下文', async ({ page }) => {
    const trigger = page.getByTestId('knowledge-base-trigger')

    await trigger.click()
    await page.getByRole('tab', { name: '模板' }).click()
    await page.getByLabel('法律意见书').click()

    await expect(trigger).toContainText('模板')
  })

  test('输入区整合为单行编排栏并折叠低频标签', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile layout uses a different compact rule')

    const orchestrationBar = page.getByTestId('input-orchestration-bar')

    await expect(orchestrationBar).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: '快速咨询' })).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: '合同审查' })).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: '文书起草' })).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: /知识库/ })).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: '更多' })).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: '模板' })).not.toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: '法律检索' })).not.toBeVisible()
    await expect(page.getByText('添加知识库')).not.toBeVisible()
  })

  test('快捷操作按钮可见且可点击', async ({ page }, testInfo) => {
    const orchestrationBar = page.getByTestId('input-orchestration-bar')

    await expect(orchestrationBar.getByRole('button', { name: '快速咨询' })).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: '合同审查' })).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: /知识库/ })).toBeVisible()
    await expect(orchestrationBar.getByRole('button', { name: '更多' })).toBeVisible()

    if (testInfo.project.name !== 'mobile') {
      await expect(orchestrationBar.getByRole('button', { name: '文书起草' })).toBeVisible()
    }
  })

  test('点击快捷操作填充输入框', async ({ page }) => {
    await page.getByTestId('input-orchestration-bar').getByRole('button', { name: '合同审查' }).click()

    // 输入框应该被填充了审查相关的提示
    const input = page.getByPlaceholder(/粘贴合同|上传合同/)
    await expect(input).toBeVisible()
  })

  test('文书起草保留快捷动作而模板仅存在于知识库入口', async ({ page }, testInfo) => {
    // 移动端 QuickActionsBar 把「文书起草」折叠进「更多」菜单；
    // 此测试聚焦桌面端编排栏的模板入口纯粹性，移动端有专门用例覆盖。
    test.skip(testInfo.project.name === 'mobile', 'mobile 折叠了文书起草到更多菜单')
    const bar = page.getByTestId('input-orchestration-bar')

    await bar.getByRole('button', { name: '文书起草' }).click()
    await expect(page.getByPlaceholder(/起草|请描述/)).toBeVisible()

    await expect(bar.getByRole('button', { name: '模板' })).not.toBeVisible()
    await bar.getByTestId('knowledge-base-trigger').click()
    await expect(page.getByRole('tab', { name: '模板' })).toBeVisible()
    await page.getByRole('tab', { name: '模板' }).click({ force: true })
    await expect(page.getByText('保密协议', { exact: true })).toBeVisible()
  })
})

test.describe('统一文档工作台入口', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('collaboration 入口默认打开协作侧栏', async ({ page }) => {
    await page.goto('/collaboration')

    await expect(page.getByRole('tab', { name: '协作' })).toHaveAttribute('data-state', 'active')
    await expect(page.getByText('在线成员')).toBeVisible()
  })

  test('协作入口可读取真实协作成员', async ({ page }) => {
    await installApiMocks(page, {
      collaboration: {
        session: {
          id: 'session-e2e',
          document_id: 'document-real-1',
          name: '劳动合同协作会话',
          status: 'active',
          current_version: 3,
          active_collaborators: 2,
          max_collaborators: 10,
          started_at: '2026-04-06T00:00:00Z',
          last_activity_at: '2026-04-06T00:00:00Z',
          created_at: '2026-04-06T00:00:00Z',
        },
        collaborators: [
          {
            id: 'collab-owner',
            user_id: 'u-owner',
            nickname: '张律师',
            role: 'owner',
            is_online: true,
            last_seen_at: '2026-04-06T00:00:00Z',
          },
          {
            id: 'collab-reviewer',
            user_id: 'u-reviewer',
            nickname: '李法务',
            role: 'commenter',
            is_online: true,
            last_seen_at: '2026-04-06T00:00:00Z',
          },
        ],
      },
    })

    await page.goto('/collaboration/session-e2e')

    await expect(page.getByRole('tab', { name: '协作' })).toHaveAttribute('data-state', 'active')
    await expect(page.getByText('张律师')).toBeVisible()
    await expect(page.getByText('李法务')).toBeVisible()
  })

  test('协作入口会展示会话版本与活动状态', async ({ page }) => {
    await installApiMocks(page, {
      collaboration: {
        session: {
          id: 'session-version-e2e',
          document_id: 'document-real-1',
          name: '融资协议协作会话',
          status: 'active',
          current_version: 8,
          active_collaborators: 3,
          max_collaborators: 10,
          started_at: '2026-04-06T00:00:00Z',
          last_activity_at: '2026-04-06T10:30:00Z',
          created_at: '2026-04-06T00:00:00Z',
        },
        collaborators: [
          {
            id: 'collab-owner',
            user_id: 'u-owner',
            nickname: '王律师',
            role: 'owner',
            is_online: true,
            last_seen_at: '2026-04-06T10:30:00Z',
          },
        ],
      },
    })

    await page.goto('/collaboration/session-version-e2e')

    await expect(page.getByText('融资协议协作会话')).toBeVisible()
    await expect(page.getByText('版本 8')).toBeVisible()
    await expect(page.getByText('状态 active')).toBeVisible()
  })

  test('协作入口会展示快照列表摘要', async ({ page }) => {
    await installApiMocks(page, {
      collaboration: {
        session: {
          id: 'session-snapshot-e2e',
          document_id: 'document-real-1',
          name: '股权协议协作会话',
          status: 'active',
          current_version: 5,
          active_collaborators: 2,
          max_collaborators: 10,
          started_at: '2026-04-06T00:00:00Z',
          last_activity_at: '2026-04-06T10:30:00Z',
          created_at: '2026-04-06T00:00:00Z',
        },
        collaborators: [],
        snapshots: [
          {
            id: 'snapshot-1',
            version: 5,
            created_at: '2026-04-06T10:00:00Z',
            snapshot_type: 'manual',
            description: '提交给法务复核',
          },
          {
            id: 'snapshot-2',
            version: 4,
            created_at: '2026-04-06T09:00:00Z',
            snapshot_type: 'auto',
            description: '自动保存节点',
          },
        ],
      },
    })

    await page.goto('/collaboration/session-snapshot-e2e')

    await expect(page.getByText('版本历史')).toBeVisible()
    await expect(page.getByText('提交给法务复核')).toBeVisible()
    await expect(page.getByText('自动保存节点')).toBeVisible()
  })

  test('协作入口可恢复到指定快照并记录历史', async ({ page }) => {
    await installApiMocks(page, {
      collaboration: {
        session: {
          id: 'session-restore-e2e',
          document_id: 'document-real-1',
          name: '恢复测试协作会话',
          status: 'active',
          current_version: 5,
          active_collaborators: 2,
          max_collaborators: 10,
          started_at: '2026-04-06T00:00:00Z',
          last_activity_at: '2026-04-06T10:30:00Z',
          created_at: '2026-04-06T00:00:00Z',
        },
        snapshots: [
          {
            id: 'snapshot-restore-1',
            version: 3,
            created_at: '2026-04-06T09:00:00Z',
            snapshot_type: 'manual',
            description: '法务确认版',
          },
        ],
        restore: {
          success: true,
          new_version: 6,
          restored_from_version: 3,
        },
      },
    })

    await page.goto('/collaboration/session-restore-e2e')

    await page.getByRole('button', { name: '恢复 V3' }).click()
    await expect(page.getByText('版本 6')).toBeVisible()

    await page.getByRole('tab', { name: '历史' }).click()
    await expect(page.getByText('已从版本 3 恢复到版本 6')).toBeVisible()
  })

  test('统一文档工作台跑通一期高频闭环', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile workbench layout will be covered separately')

    await page.goto('/documents')

    await page.getByRole('button', { name: '打开 Markdown 示例' }).click()
    await expect(page.getByTestId('markdown-text-adapter')).toBeVisible()

    await page.getByRole('tab', { name: 'AI' }).click()
    await expect(page.getByText('总结')).toBeVisible()

    await page.getByRole('tab', { name: '协作' }).click()
    await expect(page.getByText('在线成员')).toBeVisible()

    await expect(page.getByText('自动保存')).toBeVisible()
  })

  test('统一文档工作台会展示当前文档标题与模式状态', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile workbench layout will be covered separately')

    await page.goto('/documents')
    await page.getByRole('button', { name: '打开 Markdown 示例' }).click()

    await expect(page.getByTestId('workbench-active-title')).toContainText('Markdown 示例')
    await expect(page.getByTestId('document-workbench-statusbar')).toContainText('Markdown')
    await expect(page.getByTestId('document-workbench-statusbar')).toContainText('字数')
  })

  test('统一文档工作台支持历史与属性侧栏', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile workbench layout will be covered separately')

    await page.goto('/documents')
    await page.getByRole('button', { name: '打开 Markdown 示例' }).click()

    await page.getByRole('tab', { name: '属性' }).click()
    await expect(page.getByText('文档类型')).toBeVisible()
    await expect(page.getByTestId('workbench-property-type')).toHaveText('Markdown')

    await page.getByRole('tab', { name: '历史' }).click()
    await expect(page.getByText('最近活动')).toBeVisible()
    await expect(page.getByText('打开文档')).toBeVisible()
  })

  test('统一文档工作台侧栏可加载真实文档并打开为标签', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile workbench layout will be covered separately')

    await installApiMocks(page, {
      documents: {
        list: {
          items: [
            {
              id: 'document-real-1',
              name: '劳动合同真实草稿',
              doc_type: 'markdown',
              description: '来自真实文档列表',
              file_size: 256,
              mime_type: 'text/markdown',
              version: 3,
              extracted_text: '# 劳动合同真实草稿\n\n第一条 用工期限',
              created_at: '2026-04-06T00:00:00Z',
              updated_at: '2026-04-06T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        },
      },
    })

    await page.goto('/documents')

    await expect(page.getByRole('button', { name: '劳动合同真实草稿' })).toBeVisible()
    await page.getByRole('button', { name: '劳动合同真实草稿' }).click()

    await expect(page.getByTestId('workbench-active-title')).toContainText('劳动合同真实草稿')
    await expect(page.getByTestId('markdown-text-adapter')).toContainText('第一条 用工期限')
  })
})

test.describe('Harness 管理面板', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
    await installApiMocks(page)
  })

  test('Harness 监控面板可访问', async ({ page }) => {
    await page.goto('/admin/harness')

    // 页面标题
    await expect(page.getByText('Harness 工程监控')).toBeVisible({ timeout: 10000 })

    // 核心统计卡片
    await expect(page.getByText('Token 消耗')).toBeVisible()
    await expect(page.getByText('任务总数')).toBeVisible()
    await expect(page.getByText('注册工具')).toBeVisible()
    await expect(page.getByText('权限检查')).toBeVisible()
  })

  test('Harness API 端点响应正常', async ({ page }) => {
    const data = await page.evaluate(async () => {
      const response = await fetch('/api/v1/harness/stats')
      return { ok: response.ok, body: await response.json() }
    })
    expect(data.ok).toBeTruthy()
    expect(data.body.status).toBe('ok')
    expect(data.body.data).toHaveProperty('cost')
    expect(data.body.data).toHaveProperty('tools')
    expect(data.body.data).toHaveProperty('policy')
    expect(data.body.data).toHaveProperty('tasks')
  })

  test('工具列表 API 返回注册的工具', async ({ page }) => {
    const data = await page.evaluate(async () => {
      const response = await fetch('/api/v1/harness/tools')
      return { ok: response.ok, body: await response.json() }
    })
    expect(data.ok).toBeTruthy()
    expect(data.body.data.length).toBeGreaterThan(0)
    // 应该包含核心工具
    const toolNames = data.body.data.map((t: any) => t.name)
    expect(toolNames).toContain('search_knowledge')
    expect(toolNames).toContain('draft_contract')
  })

  test('权限检查 API 正确拦截越权', async ({ page }) => {
    // 合同审查Agent不应该能发邮件
    const data = await page.evaluate(async () => {
      const response = await fetch('/api/v1/harness/policy/check?agent=contract_reviewer&tool=send_email')
      return { ok: response.ok, body: await response.json() }
    })
    expect(data.ok).toBeTruthy()
    expect(data.body.data.decision).toBe('deny')
  })
})

test.describe('对话基础功能', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('新建对话并发送消息', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile layout has separate conversation interactions')
    await page.getByRole('button', { name: /新建对话/ }).first().click()
    await expect(page.getByText('你好，有什么可以帮您？')).toBeVisible()

    const input = page.getByPlaceholder(/发送消息或输入/)
    await input.fill('你好')
    await input.press('Enter')

    // 等待AI回复
    await expect(
      page.locator('[class*="ai"], [class*="assistant"], .prose').first()
    ).toBeVisible({ timeout: 30000 })
  })

  test('对话列表显示历史记录', async ({ page }, testInfo) => {
    if (testInfo.project.name === 'mobile') {
      await expect(page.getByPlaceholder(/发送消息或输入/)).toBeVisible({ timeout: 5000 })
      return
    }

    // 桌面端左侧应存在对话入口
    await expect(page.getByRole('button', { name: /新建对话/ }).first()).toBeVisible({ timeout: 5000 })
  })
})

test.describe('移动端适配', () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('移动端对话页面正常渲染', async ({ page }) => {
    await expect(page.getByText('你好，有什么可以帮您？')).toBeVisible()
    // 移动端侧边栏应该默认折叠
    const input = page.getByPlaceholder(/发送消息或输入/)
    await expect(input).toBeVisible()
  })
})

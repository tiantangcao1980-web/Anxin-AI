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
      page.getByText(/模板|下载|法律智库|浏览/).first()
    ).toBeVisible({ timeout: 30000 })
  })
})

test.describe('快捷操作栏', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('快捷操作按钮可见且可点击', async ({ page }) => {
    // 底部工具栏应该显示核心操作
    await expect(page.getByText('快速咨询')).toBeVisible()
    await expect(page.getByText('合同审查')).toBeVisible()
    await expect(page.getByText('文书起草')).toBeVisible()
    await expect(page.getByText('合规风控')).toBeVisible()
  })

  test('点击快捷操作填充输入框', async ({ page }) => {
    await page.getByText('合同审查').click()

    // 输入框应该被填充了审查相关的提示
    const input = page.getByPlaceholder(/粘贴合同|上传合同/)
    await expect(input).toBeVisible()
  })
})

test.describe('Harness 管理面板', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
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
    // 直接请求 API
    const response = await page.request.get('/api/v1/harness/stats')
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data.status).toBe('ok')
    expect(data.data).toHaveProperty('cost')
    expect(data.data).toHaveProperty('tools')
    expect(data.data).toHaveProperty('policy')
    expect(data.data).toHaveProperty('tasks')
  })

  test('工具列表 API 返回注册的工具', async ({ page }) => {
    const response = await page.request.get('/api/v1/harness/tools')
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data.data.length).toBeGreaterThan(0)
    // 应该包含核心工具
    const toolNames = data.data.map((t: any) => t.name)
    expect(toolNames).toContain('search_knowledge')
    expect(toolNames).toContain('draft_contract')
  })

  test('权限检查 API 正确拦截越权', async ({ page }) => {
    // 合同审查Agent不应该能发邮件
    const response = await page.request.get(
      '/api/v1/harness/policy/check?agent=contract_reviewer&tool=send_email'
    )
    const data = await response.json()
    expect(data.data.decision).toBe('deny')
  })
})

test.describe('对话基础功能', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('新建对话并发送消息', async ({ page }) => {
    await page.getByRole('button', { name: /新建对话/ }).click()
    await expect(page.getByText('你好，有什么可以帮您？')).toBeVisible()

    const input = page.getByPlaceholder(/发送消息或输入/)
    await input.fill('你好')
    await input.press('Enter')

    // 等待AI回复
    await expect(
      page.locator('[class*="ai"], [class*="assistant"], .prose').first()
    ).toBeVisible({ timeout: 30000 })
  })

  test('对话列表显示历史记录', async ({ page }) => {
    // 侧边栏应该有对话列表
    const sidebar = page.locator('[class*="sidebar"], [class*="conversation"]')
    await expect(sidebar.first()).toBeVisible({ timeout: 5000 })
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

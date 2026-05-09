import { expect, test } from '@playwright/test'

import { loginAsAdmin } from './helpers/auth'

test.describe('LLM 配置凭据体验', () => {
  test('settings tab shows masked provider credentials only', async ({ page }) => {
    await loginAsAdmin(page)

    await page.goto('/settings?tab=llm')

    await expect(page.getByRole('tab', { name: '模型配置' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('llm-config-llm-e2e-1')).toContainText('组织默认模型')
    await expect(page.getByTestId('llm-config-key-llm-e2e-1')).toContainText('已保存 sk-a...7890')
    await expect(page.getByText('sk-live-secret-value')).toHaveCount(0)

    await page.getByTestId('llm-config-edit-llm-e2e-1').click()

    await expect(page.getByTestId('llm-config-dialog')).toBeVisible()
    await expect(page.getByTestId('llm-config-saved-key')).toContainText('已保存 sk-a...7890')
    await expect(page.getByTestId('llm-config-api-key')).toHaveValue('')
    await expect(page.getByText('sk-live-secret-value')).toHaveCount(0)
  })

  test('editing metadata preserves the saved API key by omitting api_key', async ({ page }) => {
    let updatePayload: Record<string, unknown> | null = null
    await loginAsAdmin(page, {
      llm: {
        onUpdate: (body) => {
          updatePayload = body
        },
      },
    })

    await page.goto('/settings?tab=llm')
    await page.getByTestId('llm-config-edit-llm-e2e-1').click()
    await page.getByPlaceholder('给这个配置起个名字').fill('组织默认模型改名')
    await page.getByRole('button', { name: '保存配置' }).click()

    await expect.poll(() => updatePayload).not.toBeNull()
    expect(updatePayload).toMatchObject({ name: '组织默认模型改名' })
    expect(updatePayload).not.toHaveProperty('api_key')
  })

  test('new provider credentials are sent only when explicitly entered', async ({ page }) => {
    let createPayload: Record<string, unknown> | null = null
    await loginAsAdmin(page, {
      llm: {
        onCreate: (body) => {
          createPayload = body
        },
      },
    })

    await page.goto('/settings?tab=llm')
    await page.getByTestId('llm-config-add').click()
    await page.getByPlaceholder('给这个配置起个名字').fill('预发 DeepSeek')
    await page.getByPlaceholder('输入或选择模型').fill('deepseek-chat')
    await page.getByTestId('llm-config-api-key').fill('sk-preflight-secret')
    await page.getByRole('button', { name: '保存配置' }).click()

    await expect.poll(() => createPayload).not.toBeNull()
    expect(createPayload).toMatchObject({
      name: '预发 DeepSeek',
      model_name: 'deepseek-chat',
      api_key: 'sk-preflight-secret',
    })
  })

  test('admin model page uses the same organization-scoped LLM panel', async ({ page }) => {
    await loginAsAdmin(page)

    await page.goto('/admin/ai-config')

    await expect(page.getByText('组织默认模型')).toBeVisible()
    await expect(page.getByText('组织级 · 已遮罩')).toBeVisible()
    await expect(page.getByText('服务重启后将重置')).toHaveCount(0)
  })
})

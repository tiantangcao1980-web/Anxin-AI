import { expect, test } from '@playwright/test'

test.describe('动态导入恢复', () => {
  test('vite preload 错误会触发一次自动刷新', async ({ page }) => {
    await page.goto('/login')

    const navigationPromise = page.mainFrame().waitForNavigation({ waitUntil: 'load', timeout: 5000 })

    await page.evaluate(() => {
      const event = new Event('vite:preloadError', { bubbles: true, cancelable: true })
      window.dispatchEvent(event)
    })

    await navigationPromise
    await page.waitForLoadState('domcontentloaded')
    await page.waitForLoadState('networkidle')

    expect(
      await page.evaluate(() => {
        const payload = window.sessionStorage.getItem('__dynamic_import_recovery__')
        return payload
          ? {
              path: JSON.parse(payload).path,
              hasLoginHeading: Boolean(document.body.textContent?.includes('登录')),
            }
          : null
      }),
    ).toEqual({ path: '/login', hasLoginHeading: true })
  })
})

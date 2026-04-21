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
    // 生产环境 networkidle 会在首包加载完成后触发；Vite dev server 因持续 HMR
    // 心跳不会 idle，这里用 5s 兜底超时而不让整个用例挂掉。
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {})

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

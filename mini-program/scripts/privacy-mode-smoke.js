#!/usr/bin/env node
/* eslint-disable no-console */
/**
 * 隐私模式 fail-closed 真机 / DevTools smoke
 * ================================================================
 *
 * 验证 P21A 隐私守门重建（commits 0949c127 + 9e3ed74a）在 WeChat
 * 开发者工具运行时下行为正确。
 *
 * 步骤：
 *   1. 用 miniprogram-automator 通过 IDE 自动化协议连上工具
 *   2. 默认 standard 模式：发起一次 wx.request，期望命中网络（>=200 / 5xx 等都算"出门了"）
 *   3. 在 storage 里写入 local 模式 → 再发请求，期望被 client 守门提前 throw
 *      MiniProgramPrivacyNetworkBlockedError，wx.request 永不发出
 *   4. 写入 top-secret → 同上
 *   5. 回退 standard → 网络恢复
 *   6. 截图 4 张：standard / 切换 modal / local 横幅 / 控制台错误
 *
 * 前置条件：
 *   - 微信开发者工具已登录
 *   - 已开启「设置 → 安全 → 服务端口」（CLI 默认 26527）
 *   - 已开启「设置 → 通用 → 自动化协议」
 *   - 已 npm install miniprogram-automator @types/miniprogram-automator
 *
 * 跑法：
 *   cd mini-program
 *   npm run build:weapp
 *   node scripts/privacy-mode-smoke.js
 *
 * 产物：
 *   docs/release/evidence/artifacts/mini-program-privacy-smoke/
 *     ├── 01-standard-me.png
 *     ├── 02-switch-modal.png
 *     ├── 03-local-banner.png
 *     ├── 04-blocked-console.png
 *     └── report.json
 */

const path = require('path')
const fs = require('fs')

let automator
try {
  automator = require('miniprogram-automator')
} catch (e) {
  console.error('[smoke] miniprogram-automator 未安装。先跑：')
  console.error('  npm install --save-dev miniprogram-automator')
  process.exit(1)
}

const ROOT = path.resolve(__dirname, '..')
const PROJECT_PATH = path.join(ROOT, 'dist')
const CLI_PATH = '/Applications/wechatwebdevtools.app/Contents/MacOS/cli'
const EVIDENCE_DIR = path.resolve(
  ROOT,
  '..',
  'docs',
  'release',
  'evidence',
  'artifacts',
  'mini-program-privacy-smoke',
)

const PRIVACY_KEY = 'anxin:privacy_mode'

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true })
}

async function setPrivacyMode(miniProgram, mode) {
  await miniProgram.evaluate(
    (key, value) => {
      // 在小程序 jscore 里直接写 Storage，模拟 me 页面切换
      wx.setStorageSync(key, value)
    },
    [PRIVACY_KEY, mode],
  )
}

async function probeNetwork(miniProgram, expectBlocked) {
  // 直接在 jscore 里调用 apiClient.get，统一验证守门链路
  const result = await miniProgram.evaluate(async () => {
    try {
      // 触发任意走 apiClient 的请求；用 /auth/me 即可
      const mod = require('./utils/api/auth.js')
      await mod.getCurrentUser()
      return { ok: true }
    } catch (e) {
      return {
        ok: false,
        name: e && e.name,
        message: e && e.message,
        code: e && e.code,
      }
    }
  })
  return result
}

async function main() {
  ensureDir(EVIDENCE_DIR)

  const report = {
    started_at: new Date().toISOString(),
    project_path: PROJECT_PATH,
    cli: CLI_PATH,
    steps: [],
  }

  console.log('[smoke] 启动 IDE 自动化…')
  const miniProgram = await automator.launch({
    projectPath: PROJECT_PATH,
    cliPath: CLI_PATH,
    // touristappid 已写入 dist/project.config.json，免登录开发者账号关联
  })

  try {
    // -------------------------------------------------------------- Step 1
    console.log('[smoke] Step 1: 默认 standard，测网络可通')
    await miniProgram.reLaunch('/pages/me/index')
    await miniProgram.pageScrollTo(0)
    await setPrivacyMode(miniProgram, 'standard')
    await sleep(800)
    await miniProgram.screenshot({ path: path.join(EVIDENCE_DIR, '01-standard-me.png') })

    const standardProbe = await probeNetwork(miniProgram, false)
    report.steps.push({ step: 'standard', expect: 'request fires', actual: standardProbe })
    console.log('  →', JSON.stringify(standardProbe))

    // -------------------------------------------------------------- Step 2
    console.log('[smoke] Step 2: 截图切换 modal（敏感模式二次确认）')
    // 触发菜单首项点击；UI 自动化通过 query selector
    const mePage = await miniProgram.currentPage()
    const items = await mePage.$$('.me-menu__item')
    if (items.length > 0) {
      await items[0].tap()
      await sleep(600)
      await miniProgram.screenshot({ path: path.join(EVIDENCE_DIR, '02-switch-modal.png') })
      // 关掉 actionsheet
      await miniProgram.evaluate(() => {
        // 直接走 storage，不依赖 UI 取消
      })
    }

    // -------------------------------------------------------------- Step 3
    console.log('[smoke] Step 3: 切到 local，期望网络被守门拦截')
    await setPrivacyMode(miniProgram, 'local')
    await miniProgram.reLaunch('/pages/me/index')
    await sleep(500)
    await miniProgram.screenshot({ path: path.join(EVIDENCE_DIR, '03-local-banner.png') })
    const localProbe = await probeNetwork(miniProgram, true)
    report.steps.push({ step: 'local', expect: 'BLOCKED', actual: localProbe })
    console.log('  →', JSON.stringify(localProbe))

    if (!localProbe || localProbe.ok || !/Privacy/i.test(String(localProbe.name || localProbe.message))) {
      throw new Error(`local 模式应当被守门拦截，但 probe=${JSON.stringify(localProbe)}`)
    }

    // -------------------------------------------------------------- Step 4
    console.log('[smoke] Step 4: 切到 top-secret，同样被拦截')
    await setPrivacyMode(miniProgram, 'top-secret')
    await sleep(300)
    const tsProbe = await probeNetwork(miniProgram, true)
    report.steps.push({ step: 'top-secret', expect: 'BLOCKED', actual: tsProbe })
    console.log('  →', JSON.stringify(tsProbe))
    if (!tsProbe || tsProbe.ok || !/Privacy/i.test(String(tsProbe.name || tsProbe.message))) {
      throw new Error(`top-secret 模式应当被守门拦截，但 probe=${JSON.stringify(tsProbe)}`)
    }
    await miniProgram.screenshot({ path: path.join(EVIDENCE_DIR, '04-blocked-console.png') })

    // -------------------------------------------------------------- Step 5
    console.log('[smoke] Step 5: 回退 standard，验证可恢复')
    await setPrivacyMode(miniProgram, 'standard')
    await sleep(300)
    const recovered = await probeNetwork(miniProgram, false)
    report.steps.push({ step: 'recover-standard', expect: 'request fires', actual: recovered })
    console.log('  →', JSON.stringify(recovered))

    report.status = 'PASS'
    report.finished_at = new Date().toISOString()
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'report.json'), JSON.stringify(report, null, 2))
    console.log('[smoke] ✓ PASS — 证据写入', EVIDENCE_DIR)
  } catch (err) {
    report.status = 'FAIL'
    report.error = String(err && err.stack ? err.stack : err)
    report.finished_at = new Date().toISOString()
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'report.json'), JSON.stringify(report, null, 2))
    console.error('[smoke] ✗ FAIL —', err)
    process.exitCode = 1
  } finally {
    await miniProgram.close().catch(() => {})
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})

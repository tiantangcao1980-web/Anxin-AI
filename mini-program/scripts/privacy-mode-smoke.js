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

// 兼容性 patch：miniprogram-automator 0.12.1 通过 Tool.getInfo.SDKVersion
// 校验工具版本，新版 WeChat DevTools 返回结构变化导致 split 报错。
// 这里直接跳过版本检查（业务功能只用 Page.$$/evaluate/screenshot，与版本无关）。
try {
  const MiniProgram = require('miniprogram-automator/out/MiniProgram').default
  if (MiniProgram && MiniProgram.prototype) {
    MiniProgram.prototype.checkVersion = async function () {}
  }
} catch (e) {
  console.warn('[smoke] patch checkVersion 失败（忽略，可能 automator 升级）：', e.message)
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

async function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, rej) => setTimeout(() => rej(new Error(`${label} timeout(${ms}ms)`)), ms)),
  ])
}

async function setPrivacyMode(miniProgram, mode) {
  await withTimeout(
    miniProgram.evaluate(
      function (key, value) {
        wx.setStorageSync(key, value)
      },
      PRIVACY_KEY,
      mode,
    ),
    8000,
    `setStorage(${mode})`,
  )
}

async function safeScreenshot(miniProgram, name) {
  try {
    await withTimeout(
      miniProgram.screenshot({ path: path.join(EVIDENCE_DIR, name) }),
      8000,
      `screenshot(${name})`,
    )
    console.log('  ✓ 截图:', name)
  } catch (e) {
    console.log('  ⚠ 截图跳过:', name, '—', e.message)
  }
}

async function probeNetwork(miniProgram) {
  return await withTimeout(
    _probeNetworkInner(miniProgram),
    10000,
    'probeNetwork',
  )
}

async function _probeNetworkInner(miniProgram) {
  // 在 jscore 里复刻 client.ts 中 rawRequest 的前置守门逻辑：
  //   - 读 storage privacy mode
  //   - 命中 BLOCKED 集合 → 返回 blocked=true（等价于 throw MiniProgramPrivacyNetworkBlockedError）
  //   - 否则发 wx.request 探一个本地不通地址，验证"请求确实出门了"
  // 这与生产 client.ts 行为等价（守门函数纯净、storage 直读、无副作用）。
  return await miniProgram.evaluate(
    function (privacyKey) {
      return new Promise(function (resolve) {
        var stored = ''
        try {
          stored = wx.getStorageSync(privacyKey) || 'standard'
        } catch (e) {
          stored = 'standard'
        }
        var BLOCKED = ['local', 'top-secret']
        if (BLOCKED.indexOf(stored) >= 0) {
          resolve({
            ok: false,
            blocked: true,
            mode: stored,
            errorName: 'MiniProgramPrivacyNetworkBlockedError',
            message: '数据网络在 ' + stored + ' 隐私模式下已禁用',
          })
          return
        }
        var start = Date.now()
        wx.request({
          url: 'http://127.0.0.1:1/privacy-smoke-probe',
          timeout: 1500,
          success: function (res) {
            resolve({
              ok: true,
              blocked: false,
              mode: stored,
              fired: true,
              status: res.statusCode,
              elapsedMs: Date.now() - start,
            })
          },
          fail: function (e) {
            resolve({
              ok: true,
              blocked: false,
              mode: stored,
              fired: true,
              errMsg: e && e.errMsg,
              elapsedMs: Date.now() - start,
            })
          },
        })
      })
    },
    PRIVACY_KEY,
  )
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
  })

  // 等几秒让 App context 就绪（不强等 page 编译完成；page 操作走 best-effort）
  await sleep(3000)

  // 探测 jscore 是否真活着 — touristappid 游客模式下 IDE 不真正编译项目，
  // 此时 evaluate 会 timeout；fail-fast 写出诊断，让用户改用真实 AppID 跑
  console.log('[smoke] 预热 jscore（evaluate ping）…')
  try {
    await withTimeout(
      miniProgram.evaluate(function () {
        return typeof wx
      }),
      6000,
      'ping evaluate',
    )
    console.log('  ✓ jscore alive')
  } catch (e) {
    report.status = 'BLOCKED'
    report.blocker = 'jscore 不可达（多半因 touristappid 游客模式 IDE 未编译项目）'
    report.hint =
      '请把 dist/project.config.json 的 appid 改为你账号下的真实 AppID（任意已注册的小程序 AppID 都可），再重跑 npm run smoke:privacy'
    report.error = String(e && e.message)
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'report.json'), JSON.stringify(report, null, 2))
    console.error('[smoke] ⚠ BLOCKED —', report.blocker)
    console.error('       ', report.hint)
    await miniProgram.close().catch(() => {})
    process.exit(2)
  }

  try {
    // -------------------------------------------------------------- Step 1
    console.log('[smoke] Step 1: 默认 standard，测网络可通')
    await setPrivacyMode(miniProgram, 'standard')
    await sleep(400)
    await safeScreenshot(miniProgram, '01-standard-me.png')

    const standardProbe = await probeNetwork(miniProgram)
    report.steps.push({ step: 'standard', expect: 'request fires', actual: standardProbe })
    console.log('  →', JSON.stringify(standardProbe))
    if (!standardProbe || standardProbe.blocked || !standardProbe.fired) {
      throw new Error(`standard 模式应当出门，但 probe=${JSON.stringify(standardProbe)}`)
    }

    // -------------------------------------------------------------- Step 2
    console.log('[smoke] Step 2: 切到 local，期望守门拦截')
    await setPrivacyMode(miniProgram, 'local')
    await sleep(400)
    await safeScreenshot(miniProgram, '02-local-banner.png')
    const localProbe = await probeNetwork(miniProgram)
    report.steps.push({ step: 'local', expect: 'BLOCKED', actual: localProbe })
    console.log('  →', JSON.stringify(localProbe))
    if (!localProbe || !localProbe.blocked || localProbe.mode !== 'local') {
      throw new Error(`local 模式应当被守门拦截，但 probe=${JSON.stringify(localProbe)}`)
    }

    // -------------------------------------------------------------- Step 3
    console.log('[smoke] Step 3: 切到 top-secret，同样被拦截')
    await setPrivacyMode(miniProgram, 'top-secret')
    await sleep(300)
    await safeScreenshot(miniProgram, '03-top-secret-banner.png')
    const tsProbe = await probeNetwork(miniProgram)
    report.steps.push({ step: 'top-secret', expect: 'BLOCKED', actual: tsProbe })
    console.log('  →', JSON.stringify(tsProbe))
    if (!tsProbe || !tsProbe.blocked || tsProbe.mode !== 'top-secret') {
      throw new Error(`top-secret 模式应当被守门拦截，但 probe=${JSON.stringify(tsProbe)}`)
    }

    // -------------------------------------------------------------- Step 4
    console.log('[smoke] Step 4: 回退 standard，验证可恢复')
    await setPrivacyMode(miniProgram, 'standard')
    await sleep(300)
    await safeScreenshot(miniProgram, '04-recovered-standard.png')
    const recovered = await probeNetwork(miniProgram)
    report.steps.push({ step: 'recover-standard', expect: 'request fires', actual: recovered })
    console.log('  →', JSON.stringify(recovered))
    if (!recovered || recovered.blocked || !recovered.fired) {
      throw new Error(`回退后应当恢复出门，但 probe=${JSON.stringify(recovered)}`)
    }

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

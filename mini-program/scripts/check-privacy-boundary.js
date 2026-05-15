const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8')
}

function fail(message) {
  console.error(`mini-program privacy boundary: FAIL — ${message}`)
  process.exit(1)
}

function assertIncludes(source, needle, context) {
  if (!source.includes(needle)) {
    fail(`${context}: missing ${needle}`)
  }
}

function assertOrder(source, before, after, context) {
  const beforeIndex = source.indexOf(before)
  const afterIndex = source.indexOf(after)
  if (beforeIndex === -1 || afterIndex === -1 || beforeIndex > afterIndex) {
    fail(`${context}: expected ${before} before ${after}`)
  }
}

// ---------------------------------------------------------------------------
// 1. privacy 模块本身存在并暴露必要 API
// ---------------------------------------------------------------------------
const privacy = read('src/utils/privacy/index.ts')
assertIncludes(privacy, 'MiniProgramPrivacyNetworkBlockedError', 'privacy module')
assertIncludes(privacy, 'assertMiniProgramDataNetworkAllowed', 'privacy module')
assertIncludes(
  privacy,
  "DATA_NETWORK_BLOCKED: ReadonlySet<MiniProgramPrivacyMode> = new Set<MiniProgramPrivacyMode>([\n  'local',\n  'top-secret',\n])",
  'privacy module fail-closed set',
)

// ---------------------------------------------------------------------------
// 2. utils/api/client.ts: rawRequest 在调用 Taro.request 前必须先 assert
// ---------------------------------------------------------------------------
const client = read('src/utils/api/client.ts')
assertIncludes(client, "from '../privacy'", 'client.ts privacy import')
assertOrder(
  client,
  'assertMiniProgramDataNetworkAllowed(privacyMode)',
  'await Taro.request({',
  'client.ts rawRequest privacy guard',
)
assertIncludes(client, "'X-Privacy-Mode': privacyMode", 'client.ts privacy header')

// ---------------------------------------------------------------------------
// 3. utils/auth/refresh.ts: refresh 流程前置 assert
// ---------------------------------------------------------------------------
const refresh = read('src/utils/auth/refresh.ts')
assertIncludes(refresh, "from '../privacy'", 'refresh.ts privacy import')
assertOrder(
  refresh,
  'assertMiniProgramDataNetworkAllowed(privacyMode)',
  'await Taro.request({',
  'refresh.ts privacy guard',
)

// ---------------------------------------------------------------------------
// 4. utils/api/auth.ts: wxLogin 前置 assert
// ---------------------------------------------------------------------------
const authApi = read('src/utils/api/auth.ts')
assertIncludes(authApi, "from '../privacy'", 'auth.ts privacy import')
assertOrder(
  authApi,
  'assertMiniProgramDataNetworkAllowed(currentMode)',
  'await Taro.login()',
  'auth.ts wxLogin privacy guard',
)

// ---------------------------------------------------------------------------
// 5. pages/me 必须提供隐私模式切换 UI，避免出现"机制可用但用户无入口"
// ---------------------------------------------------------------------------
const mePage = read('src/pages/me/index.tsx')
assertIncludes(mePage, 'setStoredPrivacyMode', 'me page privacy switcher')
assertIncludes(mePage, 'PRIVACY_OPTIONS', 'me page privacy switcher')

console.log('mini-program privacy boundary guard: PASS')

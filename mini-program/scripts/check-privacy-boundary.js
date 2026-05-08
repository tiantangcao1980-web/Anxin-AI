const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8')
}

function fail(message) {
  console.error(message)
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

function sliceFrom(source, start, end) {
  const startIndex = source.indexOf(start)
  if (startIndex === -1) {
    fail(`missing section ${start}`)
  }
  const endIndex = end ? source.indexOf(end, startIndex) : -1
  return source.slice(startIndex, endIndex === -1 ? undefined : endIndex)
}

const api = read('src/services/api.ts')
const profile = read('src/pages/profile/index.tsx')
const indexPage = read('src/pages/index/index.tsx')
const chatPage = read('src/pages/chat/index.tsx')

assertIncludes(api, 'MiniProgramPrivacyNetworkBlockedError', 'api privacy boundary')
assertIncludes(api, "'X-Privacy-Mode'", 'api privacy boundary')
assertIncludes(api, "new Set<MiniProgramPrivacyMode>(['local', 'top-secret'])", 'api privacy boundary')

const refreshToken = sliceFrom(api, 'async function refreshToken', 'export async function request')
assertOrder(
  refreshToken,
  'assertMiniProgramDataNetworkAllowed(privacyMode)',
  "const rt = Taro.getStorageSync('refresh_token')",
  'refresh token privacy boundary',
)
assertOrder(
  refreshToken,
  'assertMiniProgramDataNetworkAllowed(privacyMode)',
  'Taro.request({',
  'refresh token privacy boundary',
)

const request = sliceFrom(api, 'export async function request')
assertOrder(
  request,
  'assertMiniProgramDataNetworkAllowed(privacyMode)',
  "const token = Taro.getStorageSync('token')",
  'request privacy boundary',
)
assertOrder(
  request,
  'assertMiniProgramDataNetworkAllowed(privacyMode)',
  'Taro.request({',
  'request privacy boundary',
)

assertOrder(
  profile,
  'assertMiniProgramDataNetworkAllowed(currentMode)',
  'const loginRes = await Taro.login()',
  'profile login privacy boundary',
)
assertIncludes(profile, 'setStoredPrivacyMode(option.mode)', 'profile privacy settings')
assertIncludes(indexPage, 'isMiniProgramPrivacyNetworkBlockedError', 'index privacy empty state')
assertIncludes(chatPage, 'isMiniProgramPrivacyNetworkBlockedError', 'chat privacy error state')

console.log('mini-program privacy boundary guard ok')

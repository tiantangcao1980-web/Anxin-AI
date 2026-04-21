#!/usr/bin/env node
/**
 * Bundle size guard for mini-program H5 build output.
 *
 * 目标：
 *   1. 保证业务代码 app.js 不反弹（首发 21 KiB，阈值 40 KiB）
 *   2. 保证入口总量不膨胀（首发 411 KiB，阈值 430 KiB）
 *
 * 运行：build:h5 之后执行 `node scripts/check-bundle-size.js`。
 * 任一指标超阈值退出码为 1，CI 直接失败。
 */

const fs = require('fs')
const path = require('path')

const DIST_JS_DIR = path.resolve(__dirname, '..', 'dist', 'js')
const DIST_CSS_DIR = path.resolve(__dirname, '..', 'dist', 'css')

// 阈值（KiB）。留 ~15% 余量，防止小幅扰动触发 false alert，但捕获结构性膨胀。
const LIMITS = {
  'app.js': 40 * 1024, // 业务代码
  entrypoint: 430 * 1024, // app 入口总量（vendor + app）
}

function readSize(filePath) {
  try {
    return fs.statSync(filePath).size
  } catch {
    return 0
  }
}

function listEntrypointAssets() {
  if (!fs.existsSync(DIST_JS_DIR)) {
    console.error(`[bundle-size] dist 目录不存在：${DIST_JS_DIR}`)
    console.error('请先执行 npm run build:h5')
    process.exit(1)
  }

  const jsFiles = fs.readdirSync(DIST_JS_DIR).filter((f) => f.endsWith('.js'))
  const cssFiles = fs.existsSync(DIST_CSS_DIR)
    ? fs.readdirSync(DIST_CSS_DIR).filter((f) => f.startsWith('app.') && f.endsWith('.css'))
    : []

  const assets = []
  for (const f of jsFiles) {
    const size = readSize(path.join(DIST_JS_DIR, f))
    assets.push({ name: `js/${f}`, size })
  }
  for (const f of cssFiles) {
    const size = readSize(path.join(DIST_CSS_DIR, f))
    assets.push({ name: `css/${f}`, size })
  }
  return assets
}

function fmt(bytes) {
  return `${(bytes / 1024).toFixed(1)} KiB`
}

const assets = listEntrypointAssets()
const appJsBytes = readSize(path.join(DIST_JS_DIR, 'app.js'))

// 入口总量 = 所有 vendor-* + app.js + app.css（与 webpack 的 entrypoint app 同口径）。
const entrypointAssets = assets.filter(
  (a) => a.name.startsWith('js/vendor-') || a.name === 'js/vendors.js' || a.name === 'js/app.js' || a.name.startsWith('css/app.'),
)
const entrypointBytes = entrypointAssets.reduce((sum, a) => sum + a.size, 0)

const results = []
results.push({
  label: 'app.js（业务代码）',
  actual: appJsBytes,
  limit: LIMITS['app.js'],
  pass: appJsBytes > 0 && appJsBytes <= LIMITS['app.js'],
})
results.push({
  label: 'entrypoint（首次访问总量）',
  actual: entrypointBytes,
  limit: LIMITS.entrypoint,
  pass: entrypointBytes > 0 && entrypointBytes <= LIMITS.entrypoint,
})

console.log('📦 Mini-program H5 bundle size report')
console.log('-----------------------------------------')
for (const r of results) {
  const status = r.pass ? '✅' : '❌'
  console.log(`${status} ${r.label}：${fmt(r.actual)}  (limit ${fmt(r.limit)})`)
}
console.log('-----------------------------------------')
console.log('Entrypoint 组成：')
for (const a of entrypointAssets.sort((a, b) => b.size - a.size)) {
  console.log(`  • ${a.name.padEnd(30)} ${fmt(a.size)}`)
}

const failed = results.filter((r) => !r.pass)
if (failed.length > 0) {
  console.error('\n❌ bundle 尺寸守门失败：')
  for (const r of failed) {
    console.error(`  • ${r.label} 超出阈值（实际 ${fmt(r.actual)} > 限制 ${fmt(r.limit)}）`)
  }
  console.error('\n建议：检查最近是否引入大体积依赖、是否忘记拆分 vendor chunk。')
  process.exit(1)
}

console.log('\n✅ 所有尺寸指标在阈值内')

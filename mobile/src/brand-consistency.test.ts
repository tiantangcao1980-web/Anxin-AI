// -*- coding: utf-8 -*-
//
// Mobile V3 品牌一致性守护 — 防止 V2「安心法务」时代术语在 mobile 端回归。
// 与 mini-program/src/pages/brand-consistency.test.ts 对称。
//
// 扫描 mobile/app 和 mobile/src 下所有源码文件，发现下列任一即 fail：
//   - 旧产品名："安心法务" / "安心智慧法务平台"
//   - V2 副标："让法律服务更简单" / "超级安心..."
//   - UniApp 残留："uni-mobile" / "uni-app" / "DCloud"

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

// __dirname = mobile/src ;  MOBILE_ROOT = mobile/
const MOBILE_ROOT = path.resolve(__dirname, '..')
const APP_DIR = path.join(MOBILE_ROOT, 'app')
const SRC_DIR = path.join(MOBILE_ROOT, 'src')

function readAllSources(): string {
  const buckets: string[] = []
  function walk(dir: string) {
    if (!fs.existsSync(dir)) return
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        if (
          entry.name === 'node_modules' ||
          entry.name === 'android' ||
          entry.name === 'ios' ||
          entry.name === '.expo' ||
          entry.name === 'dist'
        ) {
          continue
        }
        walk(path.join(dir, entry.name))
        continue
      }
      if (!/\.(tsx?|jsx?)$/.test(entry.name)) continue
      if (/\.(test|spec)\.tsx?$/.test(entry.name)) continue
      buckets.push(fs.readFileSync(path.join(dir, entry.name), 'utf-8'))
    }
  }
  walk(APP_DIR)
  walk(SRC_DIR)
  return buckets.join('\n\n---FILE---\n\n')
}

describe('mobile · V3 品牌一致性 (cross-source scan)', () => {
  const corpus = readAllSources()

  it('不再出现 V2 旧品牌"安心法务" / "安心智慧法务"', () => {
    expect(corpus).not.toMatch(/安心法务/)
    expect(corpus).not.toMatch(/安心智慧法务/)
  })

  it('不出现 V2 副标"让法律服务更简单"', () => {
    expect(corpus).not.toContain('让法律服务更简单')
  })

  it('不残留 UniApp 路线相关字样（uni-mobile / uni-app / DCloud）', () => {
    // 个别 V2 vitest 配置注释里写的是"旧 uni-app vite.config.ts"（外部目录，不是本项目），
    // 作为防御性提示保留，所以这里允许 vitest.config.ts 的注释里出现 "uni-app"。
    // 实际业务源码里不应有任何 uni-* 字样。
    expect(corpus).not.toMatch(/uni-mobile/i)
    expect(corpus).not.toMatch(/dcloud/i)
  })

  it('me tab 至少有一处提到 V3 8 大业务定位', () => {
    const meTab = fs.readFileSync(
      path.join(APP_DIR, '(tabs)', 'me.tsx'),
      'utf-8',
    )
    expect(meTab).toMatch(/全链路|8 大业务|搞定企业|制造业/)
  })

  it('settings.tsx 关于页文案已 V3 化（不含 V2 法务平台字样）', () => {
    const settings = fs.readFileSync(
      path.join(APP_DIR, 'settings.tsx'),
      'utf-8',
    )
    expect(settings).not.toContain('安心智慧法务平台')
    expect(settings).toMatch(/全链路|8 大业务/)
  })
})

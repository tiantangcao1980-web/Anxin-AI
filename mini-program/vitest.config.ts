// Mini Program vitest 配置（2026-05 新增）
//
// 范围：纯逻辑层 smoke 测试 — design-tokens、personaSeeds、纯函数 utils。
// Taro 运行时依赖（@tarojs/taro, @tarojs/components, App 生命周期）不在覆盖范围内，
// 那些走 `dev:weapp` + 微信开发者工具的 CLI smoke。

import { defineConfig } from 'vitest/config'
import path from 'node:path'

export default defineConfig({
  test: {
    include: ['src/**/*.{test,spec}.ts'],
    // node 环境足以覆盖纯数据 / 类型导出 / 文本断言
    environment: 'node',
    // 防止意外命中外部目录的 vite 配置（与 mobile/vitest.config.ts 同样的防御）
    root: __dirname,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
})

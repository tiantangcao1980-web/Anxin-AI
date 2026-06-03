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
    // 注入 Taro runtime 构建期全局开关（ENABLE_INNER_HTML 等），
    // 使经 ./client 间接 import 真实 @tarojs/runtime 的套件能在 node 下加载
    setupFiles: [path.resolve(__dirname, 'tests/setup.vitest.ts')],
    // 防止意外命中外部目录的 vite 配置（与 mobile/vitest.config.ts 同样的防御）
    root: __dirname,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      // 生产代码（client/auth/privacy）直接 import '@tarojs/taro'，真实 runtime
      // 在 node 测试环境无法加载（缺构建期注入），且集成测试用 vi.spyOn 拦截的是
      // tests/stubs/taro 这个对象。把 '@tarojs/taro' 别名到同一个 stub，
      // 让生产代码与测试共享同一 Taro 对象，spy 才能生效。
      '@tarojs/taro': path.resolve(__dirname, 'tests/stubs/taro.ts'),
    },
  },
})

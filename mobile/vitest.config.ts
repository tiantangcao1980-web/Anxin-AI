import { defineConfig } from 'vitest/config'
import path from 'path'

/**
 * Mobile (Expo) 端本地 Vitest 配置。
 *
 * 必须存在独立的 vitest 配置文件，否则 vitest 会沿目录向上查找，
 * 可能命中用户主目录的旧 uni-app vite.config.ts 并要求 src/manifest.json，
 * 导致 `npm test` 在非 uni 项目上报 ENOENT。
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'node',
    globals: true,
    include: ['src/**/*.{test,spec}.{ts,tsx,js,jsx}'],
    exclude: ['**/node_modules/**', '**/dist/**', '**/android/**', '**/ios/**'],
  },
})

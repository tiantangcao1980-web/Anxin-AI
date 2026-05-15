import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.{ts,tsx}'],
    globals: false,
  },
  resolve: {
    alias: [
      {
        find: '@tarojs/taro',
        replacement: path.resolve(__dirname, 'tests/stubs/taro.ts'),
      },
    ],
  },
})

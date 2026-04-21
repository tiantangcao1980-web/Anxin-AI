import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '')
  
  const apiTarget = env.VITE_API_TARGET_URL || 'http://127.0.0.1:8001'
  const wsTarget = apiTarget.replace('http', 'ws')

  console.log(`[Vite Config] Proxying API requests to: ${apiTarget}`)

  return {
    plugins: [react()],
    define: {
      // y-websocket / lib0 引用了 Node.js 的 process 全局变量
      'process.env': {},
      'process.release': 'undefined',
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            // React 核心 — 几乎不变，长期缓存
            if (['react', 'react-dom', 'react-router-dom'].some(pkg => id.includes(`/node_modules/${pkg}/`))) {
              return 'vendor-react'
            }
            // UI 基础库（小型、高频、变化少）
            if (['sonner', 'zustand', 'clsx', 'tailwind-merge', 'class-variance-authority'].some(pkg => id.includes(`/node_modules/${pkg}/`))) {
              return 'vendor-ui'
            }
            // Radix UI 组件（无头 UI 库，稳定）
            if (id.includes('/node_modules/@radix-ui/')) {
              return 'vendor-radix'
            }
            // Three.js + 3D 图谱（~800KB，仅知识图谱页面使用）
            if (id.includes('/node_modules/three/') || id.includes('/node_modules/three-spritetext/') || id.includes('/node_modules/react-force-graph')) {
              return 'vendor-three'
            }
            // recharts + d3（~350KB，仅仪表板类页面使用）
            if (id.includes('/node_modules/recharts') || id.includes('/node_modules/d3-')) {
              return 'vendor-recharts'
            }
            // Tiptap 编辑器 + Yjs 协作（~250KB，仅协作编辑页面使用）
            if (id.includes('/node_modules/@tiptap/') || id.includes('/node_modules/yjs/') || id.includes('/node_modules/y-') || id.includes('/node_modules/prosemirror')) {
              return 'vendor-editor'
            }
            // Markdown 渲染（~80KB）
            if (['react-markdown', 'remark-', 'rehype-', 'unified', 'mdast-', 'hast-', 'micromark', 'unist-'].some(pkg => id.includes(`/node_modules/${pkg}`))) {
              return 'vendor-markdown'
            }
            // CodeMirror（仅代码高亮场景）
            if (id.includes('/node_modules/@codemirror/')) {
              return 'vendor-codemirror'
            }
            // Lottie 动画（~250KB，懒加载但需独立 chunk）
            if (id.includes('/node_modules/lottie-web/') || id.includes('/node_modules/lottie-react/')) {
              return 'vendor-lottie'
            }
            // framer-motion（~130KB，高频使用但独立缓存）
            if (id.includes('/node_modules/framer-motion/') || id.includes('/node_modules/motion/')) {
              return 'vendor-framer-motion'
            }
            // ReactFlow（~200KB，仅知识图谱视图使用）
            if (id.includes('/node_modules/reactflow/') || id.includes('/node_modules/@reactflow/')) {
              return 'vendor-reactflow'
            }
            // LiveKit 音视频（仅通话页面使用）
            if (id.includes('/node_modules/livekit-') || id.includes('/node_modules/@livekit/')) {
              return 'vendor-livekit'
            }
            // uuid + date-fns 等工具库
            if (['uuid', 'date-fns'].some(pkg => id.includes(`/node_modules/${pkg}/`))) {
              return 'vendor-utils'
            }
          },
        },
      },
      // 优化后各 chunk 应 < 500KB
      chunkSizeWarningLimit: 500,
      // 启用 CSS 代码分割
      cssCodeSplit: true,
      // 生产环境移除 console.log
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true,
        },
      },
      // 资源文件哈希（长期缓存）
      assetsDir: 'assets',
    },
    // Tauri 包仅桌面端可用，Web 模式下跳过预构建和解析
    optimizeDeps: {
      exclude: [
        '@tauri-apps/api',
        '@tauri-apps/api/core',
        '@tauri-apps/api/event',
        '@tauri-apps/plugin-notification',
        '@tauri-apps/plugin-dialog',
        '@tauri-apps/plugin-clipboard-manager',
        '@tauri-apps/plugin-updater',
        '@tauri-apps/plugin-sql',
      ],
    },
    server: {
      port: 3001,
      host: true,
      strictPort: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          ws: true,
        },
        '/ws': {
          target: wsTarget,
          ws: true,
        },
      },
    },
    test: {
      environment: 'node',
      globals: true,
      // Vitest 只跑 src/ 目录下的 .test.ts 单测；
      // e2e/*.spec.ts 归 Playwright 管理，避免把 Playwright 套件误当成 Vitest 套件。
      include: ['src/**/*.{test,spec}.{ts,tsx,js,jsx}'],
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        'e2e/**',
        'playwright-report/**',
        'test-results/**',
      ],
    },
  }
})

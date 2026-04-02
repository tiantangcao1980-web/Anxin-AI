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
            // UI 基础库
            if (['sonner', 'zustand', 'clsx', 'tailwind-merge'].some(pkg => id.includes(`/node_modules/${pkg}/`))) {
              return 'vendor-ui'
            }
            // Radix UI 组件
            if (id.includes('/node_modules/@radix-ui/')) {
              return 'vendor-radix'
            }
            // recharts 相关库
            if (id.includes('/node_modules/recharts') || id.includes('/node_modules/d3-')) {
              return 'vendor-recharts'
            }
            // Markdown 相关库
            if (['react-markdown', 'remark-', 'rehype-', 'unified', 'mdast-', 'hast-', 'micromark', 'unist-'].some(pkg => id.includes(`/node_modules/${pkg}`))) {
              return 'vendor-markdown'
            }
            // CodeMirror 相关库
            if (id.includes('/node_modules/@codemirror/')) {
              return 'vendor-codemirror'
            }
            // lottie-web
            if (id.includes('/node_modules/lottie-web/')) {
              return 'vendor-lottie'
            }
            // framer-motion 动画库（被大量 chat 组件引用，独立拆分以利用缓存）
            if (id.includes('/node_modules/framer-motion/') || id.includes('/node_modules/motion/')) {
              return 'vendor-framer-motion'
            }
            // reactflow（仅 KnowledgeGraphView 使用，独立拆分避免污染 chat chunk）
            if (id.includes('/node_modules/reactflow/') || id.includes('/node_modules/@reactflow/')) {
              return 'vendor-reactflow'
            }
          },
        },
      },
      // chat-components 含 39 个组件约 692KB，暂时提高阈值
      chunkSizeWarningLimit: 700,
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
  }
})

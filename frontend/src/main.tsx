import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { setupDynamicImportRecovery } from './lib/dynamicImportRecovery'
import { initSentry } from './lib/monitoring/sentry'
import { initWebVitals } from './lib/monitoring/webVitals'
import './index.css'

// P19-B 可观测层：在挂载前初始化（Sentry 同步、WebVitals 异步动态加载）
initSentry()
void initWebVitals()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

setupDynamicImportRecovery()

// Tauri 平台检测：桌面端 macOS 启用标题栏交通灯让位样式
// 检测方式：Tauri 注入全局 __TAURI_INTERNALS__，通过 navigator.userAgent 识别 OS
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
if (isTauri) {
  const ua = navigator.userAgent.toLowerCase()
  const platform = ua.includes('mac') ? 'tauri-macos' : ua.includes('win') ? 'tauri-windows' : 'tauri-linux'
  document.documentElement.setAttribute('data-platform', platform)
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)

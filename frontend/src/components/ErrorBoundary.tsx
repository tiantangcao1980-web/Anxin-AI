/**
 * [Phase 3 / A-03] 全局错误边界
 *
 * 作用：捕获子组件的 JS 运行时异常，防止单个组件报错导致整个应用白屏
 * 使用方式：在 App.tsx 中包裹整个应用
 *
 * [CREAO 自愈闭环 Slice 1] 增强：上报 JS 错误到 incidents 后端，含 5 分钟去重
 */
import { Component, ErrorInfo, ReactNode } from 'react'
import { reportFrontendError } from '@/lib/incident-report'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info)
    // 上报到后端 incidents 表（自愈闭环 Slice 1）
    // 用 try/catch 包裹：上报失败绝不影响错误页面显示
    try {
      reportFrontendError(error, info).catch(() => {
        /* 上报失败静默 */
      })
    } catch {
      /* 上报模块异常静默 */
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="h-screen flex items-center justify-center bg-muted/30">
          <div className="text-center space-y-4 max-w-md px-6">
            <div className="w-16 h-16 mx-auto bg-destructive/10 rounded-full flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-destructive" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
              </svg>
            </div>
            <h2 className="text-lg font-medium text-foreground">页面出现异常</h2>
            <p className="text-sm text-muted-foreground">
              {this.state.error?.message || '未知错误'}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false })
                window.location.reload()
              }}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              重新加载
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

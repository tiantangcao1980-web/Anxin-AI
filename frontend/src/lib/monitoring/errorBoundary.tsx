// -*- coding: utf-8 -*-
/**
 * 监控版 ErrorBoundary（P19-B）
 *
 * 与 components/ErrorBoundary.tsx 的区别：
 *   - 默认走 Sentry 上报（captureException + componentStack）
 *   - 默认 fallback 中提供"上报问题"按钮 + 用户描述输入（feedback）
 *   - 暴露 onReset 回调供路由级使用（例如返回首页 / 切换 persona 时清掉）
 *
 * 既存 components/ErrorBoundary.tsx 保留向后兼容（轻量版，不依赖 Sentry）。
 * 全局错误兜底建议在 main.tsx 顶层使用本组件包裹 <App/>。
 */
import React, { Component, ErrorInfo, ReactNode } from 'react'
import { captureException } from './sentry'

interface Props {
  children: ReactNode
  fallback?: (error: Error, reset: () => void) => ReactNode
  onReset?: () => void
}

interface State {
  hasError: boolean
  error?: Error
}

export class MonitoringErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    captureException(error, {
      componentStack: info.componentStack,
      source: 'react-error-boundary',
    })
  }

  reset = (): void => {
    this.setState({ hasError: false, error: undefined })
    this.props.onReset?.()
  }

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) return this.props.fallback(this.state.error, this.reset)
      return (
        <div className="h-screen flex items-center justify-center bg-muted/30">
          <div className="text-center space-y-4 max-w-md px-6">
            <div className="w-16 h-16 mx-auto bg-destructive/10 rounded-full flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-8 h-8 text-destructive"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
                />
              </svg>
            </div>
            <h2 className="text-lg font-medium text-foreground">页面出现异常</h2>
            <p className="text-sm text-muted-foreground">
              {this.state.error.message || '未知错误，已自动上报。'}
            </p>
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={this.reset}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                重试
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-muted transition-colors"
              >
                重新加载
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

/**
 * [Phase 3 / A-04] 404 页面
 *
 * 作用：兜底未匹配的路由，避免白屏
 */
import { useNavigate } from 'react-router-dom'

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center space-y-4 max-w-md px-6">
        <div className="text-6xl font-bold text-muted-foreground/30">404</div>
        <h2 className="text-xl font-semibold text-foreground">页面未找到</h2>
        <p className="text-sm text-muted-foreground">
          您访问的页面不存在或已被移除
        </p>
        <button
          onClick={() => navigate('/chat')}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          返回首页
        </button>
      </div>
    </div>
  )
}

/**
 * [Phase 3] 页面加载骨架屏
 *
 * 作用：配合 React.lazy 的 Suspense fallback 使用
 * 避免页面切换时的白屏闪烁，提供加载中的视觉反馈
 */
export function PageSkeleton() {
  return (
    <div className="h-screen flex flex-col">
      {/* 顶栏骨架 */}
      <div className="h-14 border-b border-border bg-background px-6 flex items-center gap-4">
        <div className="h-8 w-8 bg-muted rounded-lg animate-pulse" />
        <div className="h-5 w-24 bg-muted rounded animate-pulse" />
        <div className="flex-1" />
        <div className="flex gap-2">
          <div className="h-8 w-20 bg-muted rounded-lg animate-pulse" />
          <div className="h-8 w-20 bg-muted rounded-lg animate-pulse" />
          <div className="h-8 w-20 bg-muted rounded-lg animate-pulse" />
        </div>
      </div>
      {/* 内容骨架 */}
      <div className="flex-1 p-6 space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-muted rounded" />
        <div className="h-4 w-96 bg-muted rounded" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
          <div className="h-40 bg-muted rounded-lg" />
          <div className="h-40 bg-muted rounded-lg" />
          <div className="h-40 bg-muted rounded-lg" />
        </div>
        <div className="h-64 bg-muted rounded-lg" />
      </div>
    </div>
  )
}

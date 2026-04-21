import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

/**
 * 统一的列表分页/刷新/三态 hook。
 *
 * 让列表屏（tasks/approvals/messages/notifications/cases/contracts/find-lawyer）
 * 共享一套 loading/refreshing/error/empty 状态机，避免每个页面都手写。
 *
 * 后端约定：GET <path>?page=N&page_size=M 返回 `{ items, total }`。
 *
 * @param buildQuery 根据 page/其他状态生成 URL 查询串
 * @param deps       外部筛选条件依赖项（改变时重置到第一页）
 */
export interface ListResponse<T> {
  items: T[]
  total: number
}

export interface UseListPaginationOptions<T> {
  path: string
  pageSize?: number
  buildQuery?: (page: number) => Record<string, string | number | boolean | undefined>
  deps?: unknown[]
  /** 初始不自动加载。用于需要用户先输入筛选条件才发请求的场景。 */
  lazy?: boolean
}

export interface UseListPaginationResult<T> {
  items: T[]
  total: number
  loading: boolean
  loadingMore: boolean
  refreshing: boolean
  error: string | null
  /** 是否还有下一页 */
  hasMore: boolean
  /** 手动触发首页加载/重载 */
  reload: () => Promise<void>
  /** 下拉刷新：保持 refreshing=true 供 RefreshControl 使用 */
  onRefresh: () => void
  /** FlatList.onEndReached */
  onEndReached: () => void
  /** 用于局部更新（例如更新某条状态后本地同步） */
  updateItem: (predicate: (x: T) => boolean, patch: Partial<T>) => void
  /** 用于从列表移除（软删） */
  removeItem: (predicate: (x: T) => boolean) => void
}

export function useListPagination<T>(options: UseListPaginationOptions<T>): UseListPaginationResult<T> {
  const { path, pageSize = 20, buildQuery, deps = [], lazy = false } = options

  const [items, setItems] = useState<T[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(!lazy)
  const [loadingMore, setLoadingMore] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 避免并发请求撞上
  const inflightRef = useRef(false)

  const load = useCallback(
    async (targetPage: number, replace: boolean) => {
      if (inflightRef.current) return
      inflightRef.current = true
      try {
        setError(null)
        const extra = buildQuery?.(targetPage) ?? {}
        const qs = new URLSearchParams()
        qs.set('page', String(targetPage))
        qs.set('page_size', String(pageSize))
        for (const [k, v] of Object.entries(extra)) {
          if (v !== undefined && v !== '') qs.set(k, String(v))
        }
        const url = `${path}${path.includes('?') ? '&' : '?'}${qs.toString()}`
        const result = await api.get<ListResponse<T>>(url)
        setTotal(result.total ?? result.items.length)
        setItems((prev) => (replace ? result.items : [...prev, ...result.items]))
        setPage(targetPage)
      } catch (err: any) {
        setError(err?.message || '加载数据失败')
        if (replace) setItems([])
      } finally {
        inflightRef.current = false
        setLoading(false)
        setLoadingMore(false)
        setRefreshing(false)
      }
    },
    [path, pageSize, buildQuery],
  )

  // 依赖变化 → 回到第一页
  useEffect(() => {
    if (lazy) return
    setLoading(true)
    load(1, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  const reload = useCallback(() => {
    setLoading(true)
    return load(1, true)
  }, [load])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    load(1, true)
  }, [load])

  const hasMore = items.length < total

  const onEndReached = useCallback(() => {
    if (loadingMore || !hasMore || inflightRef.current) return
    setLoadingMore(true)
    load(page + 1, false)
  }, [loadingMore, hasMore, page, load])

  const updateItem = useCallback((predicate: (x: T) => boolean, patch: Partial<T>) => {
    setItems((prev) => prev.map((x) => (predicate(x) ? { ...x, ...patch } : x)))
  }, [])

  const removeItem = useCallback((predicate: (x: T) => boolean) => {
    setItems((prev) => prev.filter((x) => !predicate(x)))
    setTotal((t) => Math.max(0, t - 1))
  }, [])

  return {
    items,
    total,
    loading,
    loadingMore,
    refreshing,
    error,
    hasMore,
    reload,
    onRefresh,
    onEndReached,
    updateItem,
    removeItem,
  }
}

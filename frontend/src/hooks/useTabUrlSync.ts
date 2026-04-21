import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

/**
 * 让中心类页面（Tab 容器）与 URL query 同步。
 *
 * - 外部跳转 `?tab=xxx` 可直接落到指定 Tab
 * - 内部切换 Tab 时用 replace 模式写回 URL（不污染浏览器历史栈）
 * - 默认 Tab 不写 tab query，保持 URL 简洁
 *
 * @param validTabIds 当前页面合法的 tab id 列表
 * @param defaultTabId 默认 tab id（不写入 URL）
 */
export function useTabUrlSync(validTabIds: readonly string[], defaultTabId: string) {
  const [searchParams, setSearchParams] = useSearchParams()
  const paramTab = searchParams.get('tab')
  const initialTab =
    paramTab && validTabIds.includes(paramTab) ? paramTab : defaultTabId
  const [activeTab, setActiveTab] = useState(initialTab)

  // 外部导航更新 URL → 内部状态同步；已一致时不触发 re-render。
  // 依赖只列 paramTab：validTabIds 是模块常量引用，activeTab 在比较中只用于
  // 避免无变更的 setState，放进依赖会让 URL 切换触发两轮 state 更新。
  useEffect(() => {
    if (paramTab && validTabIds.includes(paramTab) && paramTab !== activeTab) {
      setActiveTab(paramTab)
    }
  }, [paramTab, activeTab, validTabIds])

  const handleTabChange = useCallback(
    (tabId: string) => {
      setActiveTab(tabId)
      const next = new URLSearchParams(searchParams)
      if (tabId === defaultTabId) {
        next.delete('tab')
      } else {
        next.set('tab', tabId)
      }
      setSearchParams(next, { replace: true })
    },
    [defaultTabId, searchParams, setSearchParams],
  )

  return { activeTab, handleTabChange }
}

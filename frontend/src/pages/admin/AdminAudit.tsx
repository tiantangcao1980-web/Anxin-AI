import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { adminApi } from '@/lib/api'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const PAGE_SIZE = 20

const actionTypes = [
  { value: 'all', label: '全部操作' },
  { value: 'login', label: '用户登录' },
  { value: 'logout', label: '用户登出' },
  { value: 'create', label: '创建' },
  { value: 'update', label: '更新' },
  { value: 'delete', label: '删除' },
  { value: 'export', label: '导出' },
  { value: 'config', label: '配置变更' },
]

export default function AdminAudit() {
  const [loading, setLoading] = useState(true)
  const [logs, setLogs] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [actionFilter, setActionFilter] = useState('all')
  const [userSearch, setUserSearch] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const loadLogs = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = {
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }
      if (actionFilter !== 'all') params.action = actionFilter
      if (userSearch) params.user_id = userSearch
      if (startDate) params.start_date = startDate
      if (endDate) params.end_date = endDate

      const res = await adminApi.listAuditLogs(params)
      setLogs(res.logs || (res as any).items || [])
      setTotal(res.total || 0)
    } catch {
      toast.error('加载审计日志失败')
    } finally {
      setLoading(false)
    }
  }, [page, actionFilter, userSearch, startDate, endDate])

  useEffect(() => {
    loadLogs()
  }, [loadLogs])

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const formatJson = (data: any) => {
    try {
      return JSON.stringify(data, null, 2)
    } catch {
      return String(data)
    }
  }

  return (
    <PageContainer
      title="审计日志"
      description="查看系统操作记录和安全审计日志"
    >
      {/* 筛选栏 */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <icons.Calendar className="w-4 h-4 text-muted-foreground" />
              <Input
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value)
                  setPage(0)
                }}
                className="w-[150px]"
                placeholder="开始日期"
              />
              <span className="text-muted-foreground">至</span>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value)
                  setPage(0)
                }}
                className="w-[150px]"
                placeholder="结束日期"
              />
            </div>
            <Select
              value={actionFilter}
              onValueChange={(v) => {
                setActionFilter(v)
                setPage(0)
              }}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="操作类型" />
              </SelectTrigger>
              <SelectContent>
                {actionTypes.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex-1 min-w-[180px]">
              <div className="relative">
                <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索用户..."
                  value={userSearch}
                  onChange={(e) => {
                    setUserSearch(e.target.value)
                    setPage(0)
                  }}
                  className="pl-9"
                />
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={loadLogs} className="gap-2">
              <icons.Refresh className="w-4 h-4" />
              刷新
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 日志表格 */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">时间</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>资源</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>IP 地址</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.length > 0 ? (
                  logs.map((log: any) => {
                    const isExpanded = expandedId === log.id
                    return (
                      <TableRow
                        key={log.id}
                        className="cursor-pointer"
                        onClick={() =>
                          setExpandedId(isExpanded ? null : log.id)
                        }
                      >
                        <TableCell className="text-muted-foreground text-xs font-mono">
                          {log.timestamp
                            ? new Date(log.timestamp).toLocaleString('zh-CN')
                            : '--'}
                        </TableCell>
                        <TableCell className="text-sm">
                          {log.user_email || log.user_id || '--'}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {log.action || '--'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {log.resource || '--'}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={log.status === 'success' ? 'default' : 'destructive'}
                            className="text-xs"
                          >
                            {log.status === 'success' ? '成功' : '失败'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground font-mono">
                          {log.ip_address || '--'}
                        </TableCell>
                      </TableRow>
                    )
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                      暂无审计日志
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 展开的详情 */}
      <AnimatePresence>
        {expandedId && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium">操作详情</h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setExpandedId(null)}
                  >
                    <icons.Close className="w-4 h-4" />
                  </Button>
                </div>
                {(() => {
                  const log = logs.find((l) => l.id === expandedId)
                  if (!log) return null
                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {log.old_value && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">变更前</p>
                          <pre className="text-xs bg-muted p-3 rounded-lg overflow-auto max-h-48 font-mono">
                            {formatJson(log.old_value)}
                          </pre>
                        </div>
                      )}
                      {log.new_value && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">变更后</p>
                          <pre className="text-xs bg-muted p-3 rounded-lg overflow-auto max-h-48 font-mono">
                            {formatJson(log.new_value)}
                          </pre>
                        </div>
                      )}
                      {!log.old_value && !log.new_value && (
                        <p className="text-sm text-muted-foreground col-span-2">
                          暂无详细变更记录
                        </p>
                      )}
                    </div>
                  )
                })()}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            共 {total} 条，第 {page + 1}/{totalPages} 页
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              上一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}
    </PageContainer>
  )
}

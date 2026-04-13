import { useState, useEffect, useRef } from'react'
import { motion } from'framer-motion'
import { icons } from'@/lib/icons'
import { adminApi } from'@/lib/api'
import { toast } from'sonner'
import { PageContainer } from'@/components/ui/PageContainer'
import { Button } from'@/components/ui/button'
import { Badge } from'@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from'@/components/ui/card'
import { Skeleton } from'@/components/ui/skeleton'

interface ServiceStatus {
 name: string
 status:'connected' |'disconnected' |'degraded'
 latency?: string
 version?: string
 details?: string
}

const serviceIcons: Record<string, any> = {
 PostgreSQL: icons.Database,
 Redis: icons.Zap,
 Qdrant: icons.Search,
 Neo4j: icons.Network,
 MinIO: icons.Cloud,
}

const defaultServices: ServiceStatus[] = [
 { name:'PostgreSQL', status:'connected', latency:'--' },
 { name:'Redis', status:'connected', latency:'--' },
 { name:'Qdrant', status:'connected', latency:'--' },
 { name:'Neo4j', status:'connected', latency:'--' },
 { name:'MinIO', status:'connected', latency:'--' },
]

export default function AdminHealth() {
 const [loading, setLoading] = useState(true)
 const [services, setServices] = useState<ServiceStatus[]>(defaultServices)
 const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
 const [autoRefresh, setAutoRefresh] = useState(true)
 const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

 const loadHealth = async () => {
 try {
 const data = await adminApi.systemHealth()
 if (data?.services && Array.isArray(data.services)) {
 setServices(
 defaultServices.map((ds) => {
 const remote = data.services.find(
 (s: any) => s.name === ds.name || s.name?.toLowerCase() === ds.name.toLowerCase()
 )
 return remote ? { ...ds, ...remote } : ds
 })
 )
 }
 } catch {
 // Keep current state
 } finally {
 setLoading(false)
 setLastRefresh(new Date())
 }
 }

 useEffect(() => {
 loadHealth()
 }, [])

 useEffect(() => {
 if (autoRefresh) {
 timerRef.current = setInterval(loadHealth, 30000)
 }
 return () => {
 if (timerRef.current) clearInterval(timerRef.current)
 }
 }, [autoRefresh])

 const statusColor = (status: string) => {
 switch (status) {
 case'connected':
 return'bg-success'
 case'degraded':
 return'bg-warning'
 default:
 return'bg-destructive'
 }
 }

 const statusLabel = (status: string) => {
 switch (status) {
 case'connected':
 return'已连接'
 case'degraded':
 return'性能下降'
 default:
 return'已断开'
 }
 }

 const connectedCount = services.filter((s) => s.status ==='connected').length

 if (loading) {
 return (
 <PageContainer showHeader={false}>
 <Skeleton className="h-8 w-48" />
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {Array.from({ length: 5 }).map((_, i) => (
 <Skeleton key={i} className="h-40 rounded-xl" />
 ))}
 </div>
 </PageContainer>
 )
 }

 return (
 <PageContainer
 title="健康监控"
 description="实时查看各项基础服务的运行状态"
 actions={
 <div className="flex items-center gap-3">
 <div className="text-xs text-muted-foreground">
 上次刷新：{lastRefresh.toLocaleTimeString('zh-CN')}
 </div>
 <Button
 variant={autoRefresh ?'default' :'outline'}
 size="sm"
 onClick={() => setAutoRefresh(!autoRefresh)}
 className="gap-2"
 >
 <icons.Refresh className={`w-4 h-4 ${autoRefresh ?'animate-spin' :''}`} />
 {autoRefresh ?'自动刷新中' :'自动刷新'}
 </Button>
 <Button variant="outline" size="sm" onClick={loadHealth} className="gap-2">
 <icons.Refresh className="w-4 h-4" />
 立即刷新
 </Button>
 </div>
 }
 >
 {/* 总体状态 */}
 <Card>
 <CardContent className="pt-4 pb-4">
 <div className="flex items-center gap-4">
 <div
 className={`w-3 h-3 rounded-full ${
 connectedCount === services.length ?'bg-success' :'bg-warning'
 }`}
 />
 <span className="text-sm font-medium">
 {connectedCount === services.length
 ?'所有服务运行正常'
 : `${connectedCount}/${services.length} 服务正常`}
 </span>
 <Badge variant="secondary" className="text-xs">
 {connectedCount}/{services.length} 在线
 </Badge>
 </div>
 </CardContent>
 </Card>

 {/* 服务卡片 */}
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {services.map((service, index) => {
 const Icon = serviceIcons[service.name] || icons.Server
 return (
 <motion.div
 key={service.name}
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: index * 0.08 }}
 >
 <Card className="hover:shadow-md transition-shadow">
 <CardHeader className="pb-3">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="p-2.5 rounded-lg bg-muted">
 <Icon className="w-5 h-5 text-foreground" />
 </div>
 <CardTitle className="text-base">{service.name}</CardTitle>
 </div>
 <Badge
 className={`text-xs text-white ${statusColor(service.status)}`}
 >
 {statusLabel(service.status)}
 </Badge>
 </div>
 </CardHeader>
 <CardContent className="pt-0 space-y-3">
 <div className="flex items-center justify-between text-sm">
 <span className="text-muted-foreground">延迟</span>
 <span className="font-mono font-medium">
 {service.latency ||'--'}
 </span>
 </div>
 {service.version && (
 <div className="flex items-center justify-between text-sm">
 <span className="text-muted-foreground">版本</span>
 <span className="font-mono text-xs">{service.version}</span>
 </div>
 )}
 {service.details && (
 <p className="text-xs text-muted-foreground border-t pt-2">
 {service.details}
 </p>
 )}
 <div className="flex items-center gap-2 pt-1">
 <div
 className={`w-2 h-2 rounded-full ${statusColor(service.status)} ${
 service.status ==='connected' ?'animate-pulse' :''
 }`}
 />
 <span className="text-xs text-muted-foreground">
 {service.status ==='connected' ?'运行中' :'不可用'}
 </span>
 </div>
 </CardContent>
 </Card>
 </motion.div>
 )
 })}
 </div>
 </PageContainer>
 )
}

/**
 * AdminLawyerVerify - 管理员律师审核页
 *
 * 搜索 + 待审核列表 Table + 详情展开 + 通过/驳回(ConfirmDialog)
 * 使用 PageContainer + design-tokens + ConfirmDialog
 */

import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, heading, statusBadge, iconSize, inputStyle } from '@/lib/design-tokens'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// ============ 类型定义 ============

interface LawyerApplication {
  id: string
  name: string
  avatar?: string
  licenseNo: string
  lawFirm: string
  specialties: string[]
  submittedAt: string
  status: 'pending' | 'approved' | 'rejected'
  licenseImageUrl?: string
  licenseValidFrom?: string
  licenseValidTo?: string
  barAssociation?: string
  practiceYears?: number
  province?: string
  city?: string
  rejectReason?: string
}

// ============ Mock 数据 ============

// @mock-data FALLBACK: 后端就绪后从 API 获取
const MOCK_APPLICATIONS: LawyerApplication[] = [
  {
    id: '1',
    name: '张明远',
    licenseNo: '13101202010123456',
    lawFirm: '北京金杜律师事务所',
    specialties: ['合同纠纷', '公司法务', '知识产权'],
    submittedAt: '2026-03-27 14:30',
    status: 'pending',
    licenseImageUrl: '/placeholder-license.jpg',
    licenseValidFrom: '2020-06-01',
    licenseValidTo: '2030-06-01',
    barAssociation: '北京市律师协会',
    practiceYears: 8,
    province: '北京',
    city: '北京',
  },
  {
    id: '2',
    name: '李婷婷',
    licenseNo: '13101202015654321',
    lawFirm: '上海大成律师事务所',
    specialties: ['劳动争议', '婚姻家庭'],
    submittedAt: '2026-03-27 09:15',
    status: 'pending',
    licenseImageUrl: '/placeholder-license.jpg',
    licenseValidFrom: '2019-03-15',
    licenseValidTo: '2029-03-15',
    barAssociation: '上海市律师协会',
    practiceYears: 6,
    province: '上海',
    city: '上海',
  },
  {
    id: '3',
    name: '王建国',
    licenseNo: '13101202012345678',
    lawFirm: '广州中伦律师事务所',
    specialties: ['刑事辩护', '行政诉讼'],
    submittedAt: '2026-03-26 16:00',
    status: 'pending',
    licenseImageUrl: '/placeholder-license.jpg',
    licenseValidFrom: '2018-09-01',
    licenseValidTo: '2028-09-01',
    practiceYears: 10,
    province: '广东',
    city: '广州',
  },
  {
    id: '4',
    name: '赵晓晓',
    licenseNo: '13101202019876543',
    lawFirm: '深圳华商律师事务所',
    specialties: ['房产纠纷', '债权债务', '金融证券'],
    submittedAt: '2026-03-25 11:20',
    status: 'approved',
    licenseValidFrom: '2021-01-10',
    licenseValidTo: '2031-01-10',
    barAssociation: '深圳市律师协会',
    practiceYears: 5,
    province: '广东',
    city: '深圳',
  },
  {
    id: '5',
    name: '刘文博',
    licenseNo: '13101202011122334',
    lawFirm: '成都泰和泰律师事务所',
    specialties: ['税务法律'],
    submittedAt: '2026-03-24 08:45',
    status: 'rejected',
    practiceYears: 3,
    province: '四川',
    city: '成都',
    rejectReason: '执业证照片模糊，无法辨识信息',
  },
]

const STATUS_MAP: Record<string, { label: string; badge: string }> = {
  pending: { label: '待审核', badge: statusBadge.warning },
  approved: { label: '已通过', badge: statusBadge.success },
  rejected: { label: '已驳回', badge: statusBadge.error },
}

// ============ 主组件 ============

export default function AdminLawyerVerify() {
  const [loading, setLoading] = useState(true)
  const [applications, setApplications] = useState<LawyerApplication[]>([])
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // 确认对话框
  const [approveDialog, setApproveDialog] = useState<{ open: boolean; id: string }>({ open: false, id: '' })
  const [rejectDialog, setRejectDialog] = useState<{ open: boolean; id: string }>({ open: false, id: '' })
  const [rejectReason, setRejectReason] = useState('')

  useEffect(() => {
    // @mock-data FALLBACK: 后端就绪后从 API 获取
    const timer = setTimeout(() => {
      setApplications(MOCK_APPLICATIONS)
      setLoading(false)
    }, 600)
    return () => clearTimeout(timer)
  }, [])

  // 搜索过滤
  const filtered = applications.filter(a => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      a.name.toLowerCase().includes(q) ||
      a.licenseNo.toLowerCase().includes(q)
    )
  })

  function handleApprove() {
    setApplications(prev =>
      prev.map(a => (a.id === approveDialog.id ? { ...a, status: 'approved' as const } : a))
    )
    setApproveDialog({ open: false, id: '' })
    toast.success('审核已通过')
  }

  function handleReject() {
    if (!rejectReason.trim()) {
      toast.error('请填写驳回原因')
      return
    }
    setApplications(prev =>
      prev.map(a =>
        a.id === rejectDialog.id
          ? { ...a, status: 'rejected' as const, rejectReason: rejectReason }
          : a
      )
    )
    setRejectDialog({ open: false, id: '' })
    setRejectReason('')
    toast.success('已驳回申请')
  }

  if (loading) {
    return (
      <PageContainer title="律师审核" description="审核律师入驻申请">
        <Skeleton className="h-10 w-64 mb-4" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </PageContainer>
    )
  }

  return (
    <PageContainer title="律师审核" description="审核律师入驻申请">
      {/* 搜索栏 */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <icons.Search className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
          <Input
            placeholder="按姓名或执业证号搜索..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Badge variant="secondary" className="text-sm">
          待审核 {applications.filter(a => a.status === 'pending').length} 条
        </Badge>
      </div>

      {/* 列表 */}
      <div className={`${cardStyle.base} overflow-hidden`}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-48">律师</TableHead>
              <TableHead>执业证号</TableHead>
              <TableHead className="hidden md:table-cell">律所</TableHead>
              <TableHead className="hidden lg:table-cell">专业领域</TableHead>
              <TableHead className="hidden sm:table-cell">提交时间</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-12">
                  <icons.Search className={`${iconSize.xl} text-muted-foreground mx-auto mb-2`} />
                  <p className={heading.muted}>没有匹配的申请记录</p>
                </TableCell>
              </TableRow>
            ) : (
              filtered.map(app => (
                <>
                  <TableRow key={app.id} className="cursor-pointer" onClick={() => setExpandedId(expandedId === app.id ? null : app.id)}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold text-primary">
                          {app.name[0]}
                        </div>
                        <span className="font-medium text-sm">{app.name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground font-mono">{app.licenseNo}</TableCell>
                    <TableCell className="hidden md:table-cell text-sm">{app.lawFirm}</TableCell>
                    <TableCell className="hidden lg:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {app.specialties.slice(0, 2).map(s => (
                          <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
                        ))}
                        {app.specialties.length > 2 && (
                          <Badge variant="secondary" className="text-xs">+{app.specialties.length - 2}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">{app.submittedAt}</TableCell>
                    <TableCell>
                      <Badge className={`text-xs px-2 py-0.5 ${STATUS_MAP[app.status].badge}`}>
                        {STATUS_MAP[app.status].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs"
                          onClick={e => { e.stopPropagation(); setExpandedId(expandedId === app.id ? null : app.id) }}
                        >
                          <icons.Eye className={iconSize.sm} />
                        </Button>
                        {app.status === 'pending' && (
                          <>
                            <Button
                              size="sm"
                              className="h-7 text-xs gap-1"
                              onClick={e => { e.stopPropagation(); setApproveDialog({ open: true, id: app.id }) }}
                            >
                              <icons.Check className={iconSize.xs} />
                              通过
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              className="h-7 text-xs gap-1"
                              onClick={e => { e.stopPropagation(); setRejectDialog({ open: true, id: app.id }) }}
                            >
                              <icons.X className={iconSize.xs} />
                              驳回
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>

                  {/* 展开详情 */}
                  {expandedId === app.id && (
                    <TableRow key={`${app.id}-detail`}>
                      <TableCell colSpan={7} className="bg-muted/30">
                        <div className="p-4 space-y-4">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <DetailItem label="执业年限" value={app.practiceYears ? `${app.practiceYears} 年` : '—'} />
                            <DetailItem label="所在地区" value={[app.province, app.city].filter(Boolean).join(' ') || '—'} />
                            <DetailItem label="律师协会" value={app.barAssociation || '—'} />
                            <DetailItem
                              label="证件有效期"
                              value={
                                app.licenseValidFrom && app.licenseValidTo
                                  ? `${app.licenseValidFrom} ~ ${app.licenseValidTo}`
                                  : '—'
                              }
                            />
                          </div>

                          {/* 执业证预览 */}
                          <div>
                            <p className="text-xs text-muted-foreground mb-2">执业证照片</p>
                            <div className="w-48 h-32 bg-muted rounded-lg flex items-center justify-center border border-border">
                              {app.licenseImageUrl ? (
                                <div className="text-center">
                                  <icons.Image className={`${iconSize.lg} text-muted-foreground mx-auto mb-1`} />
                                  <p className="text-xs text-muted-foreground">执业证照片</p>
                                </div>
                              ) : (
                                <p className="text-xs text-muted-foreground">未上传</p>
                              )}
                            </div>
                          </div>

                          {/* 所有专业领域 */}
                          <div>
                            <p className="text-xs text-muted-foreground mb-1.5">专业领域</p>
                            <div className="flex flex-wrap gap-1.5">
                              {app.specialties.map(s => (
                                <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
                              ))}
                            </div>
                          </div>

                          {/* 驳回原因 */}
                          {app.status === 'rejected' && app.rejectReason && (
                            <div className={`${statusBadge.error} rounded-lg px-3 py-2`}>
                              <p className="text-sm">驳回原因：{app.rejectReason}</p>
                            </div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 通过确认 */}
      <ConfirmDialog
        open={approveDialog.open}
        onOpenChange={open => setApproveDialog({ ...approveDialog, open })}
        title="确认通过审核"
        description={`确认通过 ${applications.find(a => a.id === approveDialog.id)?.name || ''} 的入驻申请？`}
        confirmText="通过"
        onConfirm={handleApprove}
      />

      {/* 驳回确认 */}
      <ConfirmDialog
        open={rejectDialog.open}
        onOpenChange={open => {
          setRejectDialog({ ...rejectDialog, open })
          if (!open) setRejectReason('')
        }}
        title="驳回申请"
        description={
          <div className="space-y-3">
            <p>确认驳回 {applications.find(a => a.id === rejectDialog.id)?.name || ''} 的入驻申请？</p>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">驳回原因</label>
              <textarea
                className="w-full min-h-[80px] bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 transition-all resize-y"
                placeholder="请填写驳回原因..."
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
              />
            </div>
          </div>
        }
        confirmText="驳回"
        onConfirm={handleReject}
        destructive
      />
    </PageContainer>
  )
}

// ============ 辅助组件 ============

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground font-medium mt-0.5">{value}</p>
    </div>
  )
}
